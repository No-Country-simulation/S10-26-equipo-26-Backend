from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.store_product import StoreProductCreate, StoreProductRead
from src.services import store_product_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=StoreProductRead,
    status_code=status.HTTP_201_CREATED,
)
def create_store_product(
    payload: StoreProductCreate,
    db: DbSession,
) -> StoreProductRead:
    store_product = store_product_service.create_store_product(db, payload)
    return StoreProductRead.model_validate(store_product)


@router.get("", response_model=list[StoreProductRead])
def list_store_products(
    db: DbSession,
    tienda_id: Annotated[int | None, Query()] = None,
    producto_id: Annotated[int | None, Query()] = None,
    unmatched_only: Annotated[bool, Query()] = False,
) -> list[StoreProductRead]:
    items = store_product_service.list_store_products(
        db,
        tienda_id=tienda_id,
        producto_id=producto_id,
        unmatched_only=unmatched_only,
    )
    return [StoreProductRead.model_validate(i) for i in items]


@router.get("/{store_product_id}", response_model=StoreProductRead)
def get_store_product(
    store_product_id: int,
    db: DbSession,
) -> StoreProductRead:
    store_product = store_product_service.get_store_product(
        db,
        store_product_id,
    )
    return StoreProductRead.model_validate(store_product)
