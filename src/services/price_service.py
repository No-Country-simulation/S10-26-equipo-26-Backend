from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.schemas.precio_historico import (
    PriceHistoryList,
    PricePoint,
)
from src.services.promo_classifier import classify


def _to_price_point(row: PrecioHistorico) -> PricePoint:
    clasificacion = classify(
        precio=row.precio_local,
        precio_tachado=row.precio_tachado,
        en_oferta=row.en_oferta,
    )
    return PricePoint(
        id=row.id,
        timestamp=row.timestamp,
        producto_id=row.producto_id,
        tienda_id=row.tienda_id,
        precio_local=row.precio_local,
        precio_tachado=row.precio_tachado,
        en_oferta=row.en_oferta,
        tipo_cambio_usado=row.tipo_cambio_usado,
        precio_usd=row.precio_usd,
        raw_presentation=row.raw_presentation,
        is_promotion=clasificacion.is_promotion,
        price_regular=clasificacion.price_regular,
        discount_pct=clasificacion.discount_pct,
    )


def get_price_history(
    db: Session,
    producto_id: int | None = None,
    tienda_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 100,
) -> PriceHistoryList:
    query = select(PrecioHistorico)

    if producto_id is not None:
        existe = db.get(ProductoCanonico, producto_id)
        if existe is None:
            raise NotFoundError(f"producto {producto_id} no encontrado")
        query = query.where(PrecioHistorico.producto_id == producto_id)
    if tienda_id is not None:
        query = query.where(PrecioHistorico.tienda_id == tienda_id)
    if start is not None:
        query = query.where(PrecioHistorico.timestamp >= start)
    if end is not None:
        query = query.where(PrecioHistorico.timestamp <= end)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    assert total is not None

    rows = list(
        db.scalars(
            query.order_by(
                PrecioHistorico.timestamp.asc(),
                PrecioHistorico.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return PriceHistoryList(
        items=[_to_price_point(r) for r in rows],
        total=total,
    )
