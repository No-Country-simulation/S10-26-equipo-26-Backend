from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.categoria import CategoriaRead
from src.schemas.producto_canonico import (
    ProductoCanonicoCreate,
    ProductoCanonicoList,
    ProductoCanonicoRead,
    ProductoCanonicoUpdate,
)
from src.services import product_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/categories", response_model=list[CategoriaRead])
def list_categories(db: DbSession) -> list[CategoriaRead]:
    categorias = product_service.list_categories(db)
    return [CategoriaRead.model_validate(c) for c in categorias]


@router.get("", response_model=ProductoCanonicoList)
def list_products(
    db: DbSession,
    category_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ProductoCanonicoList:
    return product_service.list_products(
        db,
        category_id=category_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=ProductoCanonicoRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductoCanonicoCreate,
    db: DbSession,
) -> ProductoCanonicoRead:
    producto = product_service.create_product(db, payload)
    return ProductoCanonicoRead.model_validate(producto)


@router.get("/{product_id}", response_model=ProductoCanonicoRead)
def get_product(product_id: int, db: DbSession) -> ProductoCanonicoRead:
    producto = product_service.get_product(db, product_id)
    return ProductoCanonicoRead.model_validate(producto)


@router.patch("/{product_id}", response_model=ProductoCanonicoRead)
def update_product(
    product_id: int,
    payload: ProductoCanonicoUpdate,
    db: DbSession,
) -> ProductoCanonicoRead:
    producto = product_service.update_product(db, product_id, payload)
    return ProductoCanonicoRead.model_validate(producto)
