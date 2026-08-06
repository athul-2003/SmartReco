from sqlmodel import Session

from app.models.product import Product
from app.services import vector_store
from app.services.embeddings import build_embedding_text, embed_texts


class DualWriteError(Exception):
    """Raised when a catalog write can't be kept in sync across SQL + Qdrant.
    The caller's SQL transaction is always rolled back before this is raised,
    so the two stores never drift (FR-2.4/FR-2.5)."""


def _embed_and_upsert(product: Product) -> None:
    """Shared by create/update - both need the identical embed-then-upsert
    step once the SQL side has a flushed `product.id` to use as the Qdrant
    point ID. Raises DualWriteError (not the underlying exception) so
    callers have one exception type to catch and roll back on."""
    try:
        text = build_embedding_text(product.title, product.description)
        vector = embed_texts([text])[0]
        vector_store.upsert_product(
            product.id,
            vector,
            title=product.title,
            category=product.category,
            price=product.price,
        )
    except Exception as exc:
        raise DualWriteError(
            f"Failed to embed/upsert product into Qdrant: {exc}"
        ) from exc


def create_product(
    session: Session, *, title: str, description: str, category: str, price: float
) -> Product:
    product = Product(
        title=title, description=description, category=category, price=price
    )
    session.add(product)
    session.flush()  # assigns product.id without committing, so Qdrant can use it as the point ID

    try:
        _embed_and_upsert(product)
    except DualWriteError:
        session.rollback()
        raise

    session.commit()
    session.refresh(product)
    return product


def update_product(
    session: Session,
    product: Product,
    *,
    title: str,
    description: str,
    category: str,
    price: float,
) -> Product:
    product.title = title
    product.description = description
    product.category = category
    product.price = price
    session.add(product)
    session.flush()

    try:
        _embed_and_upsert(product)
    except DualWriteError:
        session.rollback()
        raise

    session.commit()
    session.refresh(product)
    return product


def delete_product(session: Session, product: Product) -> None:
    # Qdrant first: if this fails, we abort before touching SQL, so both
    # stores stay exactly as they were (safer than the reverse order, which
    # could leave an orphaned vector with no matching SQL row).
    try:
        vector_store.delete_product(product.id)
    except Exception as exc:
        raise DualWriteError(f"Failed to delete product from Qdrant: {exc}") from exc

    session.delete(product)
    session.commit()
