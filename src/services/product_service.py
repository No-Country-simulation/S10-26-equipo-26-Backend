from sqlalchemy import func, or_, select

from src.core.exceptions import NotFoundError, ValidationError
from src.models.categoria import Categoria
from src.models.producto_canonico import ProductoCanonico
from src.schemas.producto_canonico import (
    ProductoCanonicoCreate,
    ProductoCanonicoList,
    ProductoCanonicoUpdate,
)


def _get_categoria(db, categoria_id: int) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise ValidationError(f"categoria_id {categoria_id} no existe")
    return categoria


def create_product(
    db,
    payload: ProductoCanonicoCreate,
) -> ProductoCanonico:
    if payload.categoria_id is not None:
        _get_categoria(db, payload.categoria_id)

    producto = ProductoCanonico(**payload.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def get_product(db, product_id: int) -> ProductoCanonico:
    producto = db.get(ProductoCanonico, product_id)
    if producto is None:
        raise NotFoundError(f"producto {product_id} no encontrado")
    return producto


def list_products(
    db,
    category_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ProductoCanonicoList:
    query = select(ProductoCanonico)

    if category_id is not None:
        query = query.where(ProductoCanonico.categoria_id == category_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ProductoCanonico.nombre_universal.ilike(pattern),
                ProductoCanonico.marca.ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count()).select_from(query.subquery()),
    )
    assert total is not None

    query = (
        query.order_by(ProductoCanonico.nombre_universal)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(query))
    return ProductoCanonicoList(items=items, total=total)


def update_product(
    db,
    product_id: int,
    payload: ProductoCanonicoUpdate,
) -> ProductoCanonico:
    producto = get_product(db, product_id)

    cambios = payload.model_dump(exclude_unset=True)
    if "categoria_id" in cambios and cambios["categoria_id"] is not None:
        _get_categoria(db, cambios["categoria_id"])

    for campo, valor in cambios.items():
        setattr(producto, campo, valor)

    db.commit()
    db.refresh(producto)
    return producto


def list_categories(db) -> list[Categoria]:
    return list(
        db.scalars(select(Categoria).order_by(Categoria.nombre)),
    )
