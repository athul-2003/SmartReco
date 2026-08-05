"""
Loads scripts/data/courses.csv (a CC0-licensed, curated Udemy course dataset -
see docs/BUILD_PLAN.md Phase 2 for provenance), applies CATALOG_LIMIT, and
dual-writes each product to SQLite + Qdrant - the same sync guarantees admin
CRUD uses. Batches embeddings (~100/Mesh call), is resumable (skips titles
already in the DB), and retries transient Mesh failures with backoff (see
app/services/embeddings.py).
"""

import csv
import sys
from pathlib import Path

# Running this as `python scripts/seed_catalog.py` only puts scripts/ on
# sys.path, not the project root - add it so `app.*` imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine, init_db
from app.models.product import Product
from app.services import vector_store
from app.services.embeddings import build_embedding_text, embed_texts

DATA_PATH = Path(__file__).parent / "data" / "courses.csv"
BATCH_SIZE = 100


def build_description(row: dict) -> str:
    parts = [f"{row['title']} is a {row['category']} course on Udemy."]
    rating = float(row.get("rating") or 0)
    num_reviews = int(row.get("num_reviews") or 0)
    if rating and num_reviews:
        parts.append(f"Rated {rating:.1f}/5 from {num_reviews} reviews.")
    num_subscribers = int(row.get("num_subscribers") or 0)
    if num_subscribers:
        parts.append(f"{num_subscribers} students enrolled.")
    return " ".join(parts)


def load_rows(limit: int) -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit]


def seed() -> None:
    settings = get_settings()
    init_db()

    rows = load_rows(settings.catalog_limit)
    print(
        f"Loaded {len(rows)} rows from {DATA_PATH.name} (CATALOG_LIMIT={settings.catalog_limit})"
    )

    with Session(engine) as session:
        existing_titles = set(session.exec(select(Product.title)).all())

    new_rows = [r for r in rows if r["title"] not in existing_titles]
    skipped = len(rows) - len(new_rows)
    if skipped:
        print(f"Skipping {skipped} rows already seeded (resumable).")

    if not new_rows:
        print("Nothing new to seed.")
        return

    seeded = 0
    for i in range(0, len(new_rows), BATCH_SIZE):
        batch = new_rows[i : i + BATCH_SIZE]
        texts = [build_embedding_text(r["title"], build_description(r)) for r in batch]

        print(f"Embedding batch {i // BATCH_SIZE + 1} ({len(batch)} products)...")
        vectors = embed_texts(texts)

        with Session(engine) as session:
            products = []
            for row in batch:
                product = Product(
                    title=row["title"],
                    description=build_description(row),
                    category=row["category"],
                    price=float(row.get("price") or 0),
                )
                session.add(product)
                products.append(product)
            session.flush()  # assign IDs without committing, for Qdrant point IDs

            try:
                for product, vector in zip(products, vectors, strict=True):
                    vector_store.upsert_product(
                        product.id,
                        vector,
                        title=product.title,
                        category=product.category,
                        price=product.price,
                    )
            except Exception as exc:  # noqa: BLE001 - roll back on any Qdrant failure, not just specific errors
                session.rollback()
                print(f"Batch failed, rolled back: {exc}", file=sys.stderr)
                print(
                    f"Seeded {seeded} products before failure. Re-run the script to resume.",
                    file=sys.stderr,
                )
                sys.exit(1)

            session.commit()
            seeded += len(batch)

        print(f"  -> {seeded}/{len(new_rows)} new products seeded")

    with Session(engine) as session:
        sql_count = len(session.exec(select(Product.id)).all())
    qdrant_count = vector_store.count()
    print(f"\nDone. SQL products: {sql_count}, Qdrant points: {qdrant_count}")
    if sql_count != qdrant_count:
        print(
            "WARNING: SQL and Qdrant counts do not match - stores may be out of sync.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    seed()
