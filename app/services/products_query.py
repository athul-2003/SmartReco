"""
Shared product search/filter/pagination logic, used by both the public
catalog browse page (app/routers/catalog.py) and admin's course
management list (app/routers/admin.py) - identical predicate and paging
math either way, just consumed with different sort/permission needs
downstream.
"""

from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.models.product import Product


def filtered_statement(q: str, category: str) -> SelectOfScalar[Product]:
    statement = select(Product)
    if q:
        like = f"%{q}%"
        statement = statement.where(
            Product.title.ilike(like) | Product.description.ilike(like)
        )
    if category:
        statement = statement.where(Product.category == category)
    return statement


def page_numbers(page: int, total_pages: int) -> list[int | None]:
    """Truncated page list for pagination controls, e.g. [1, None, 4, 5, 6, None, 63]."""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    keep = {1, total_pages, page - 1, page, page + 1}
    keep = sorted(p for p in keep if 1 <= p <= total_pages)
    result: list[int | None] = []
    previous = None
    for p in keep:
        if previous is not None and p - previous > 1:
            result.append(None)
        result.append(p)
        previous = p
    return result
