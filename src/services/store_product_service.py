from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.producto_canonico import ProductoCanonico
from src.models.store_product import StoreProduct
from src.models.tienda import Tienda
from src.schemas.store_product import StoreProductCreate, StoreProductUpdate


def _validar_fk(db: Session, payload: StoreProductCreate) -> None:
    if payload.producto_id is not None and db.get(
        ProductoCanonico,
        payload.producto_id,
    ) is None:
        raise ValidationError(f"producto_id {payload.producto_id} no existe")
    if db.get(Tienda, payload.tienda_id) is None:
        raise ValidationError(f"tienda_id {payload.tienda_id} no existe")


def create_store_product(
    db: Session,
    payload: StoreProductCreate,
) -> StoreProduct:
    _validar_fk(db, payload)

    store_product = StoreProduct(**payload.model_dump())
    db.add(store_product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"external_id '{payload.external_id}' ya vinculado a la tienda "
            f"{payload.tienda_id}",
        ) from exc
    db.refresh(store_product)
    return store_product


def get_store_product(db: Session, store_product_id: int) -> StoreProduct:
    store_product = db.get(StoreProduct, store_product_id)
    if store_product is None:
        raise NotFoundError(f"store_product {store_product_id} no encontrado")
    return store_product


def update_store_product(
    db: Session,
    store_product_id: int,
    payload: StoreProductUpdate,
) -> StoreProduct:
    """Asigna (o desvincula con null) el producto canonico — HU 1.4 paso 4."""
    store_product = get_store_product(db, store_product_id)

    if payload.producto_id is not None:
        _validar_fk(
            db,
            StoreProductCreate(
                producto_id=payload.producto_id,
                tienda_id=store_product.tienda_id,
                external_id=store_product.external_id,
                nombre_crudo=store_product.nombre_crudo,
            ),
        )

    store_product.producto_id = payload.producto_id
    db.commit()
    db.refresh(store_product)
    return store_product


def list_store_products(
    db: Session,
    tienda_id: int | None = None,
    producto_id: int | None = None,
    unmatched_only: bool = False,
) -> list[StoreProduct]:
    query = select(StoreProduct)

    if tienda_id is not None:
        query = query.where(StoreProduct.tienda_id == tienda_id)
    if producto_id is not None:
        query = query.where(StoreProduct.producto_id == producto_id)
    if unmatched_only:
        # 0 = sin match confirmado (placeholder hasta flujo de aceptacion)
        query = query.where(StoreProduct.producto_id.is_(None))

    query = query.order_by(StoreProduct.id)
    return list(db.scalars(query))
