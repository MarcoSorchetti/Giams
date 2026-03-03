import math
from typing import Any, List


def paginate(query, page: int, per_page: int):
    """Applica paginazione a una query SQLAlchemy.

    Restituisce (items, total, page, per_page, pages).
    """
    total = query.count()
    pages = math.ceil(total / per_page) if per_page > 0 else 1
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total, page, per_page, pages


def paginated_response(items_out: List[Any], total: int, page: int, per_page: int, pages: int) -> dict:
    """Costruisce il dict di risposta paginata."""
    return {
        "items": items_out,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }
