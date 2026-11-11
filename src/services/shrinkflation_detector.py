"""Deteccion de reduflacion (HU 2.4, decision #6).

Compara la presentacion cruda (`precios_historicos.raw_presentation`)
entre observaciones consecutivas del mismo par (tienda, producto) del
`store_product` vinculado. Cambio de cantidad o de unidad => alerta
`shrinkflation` persistida en `anomaly_alerts`.

`parse_presentation` en paridad con `src/normalizers/presentation.py`
del repo Data (mismo regex, mismas aliases de unidad).
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError
from src.models.anomaly_alert import AnomalyAlert
from src.models.precio_historico import PrecioHistorico
from src.models.store_product import StoreProduct

_PRESENTATION_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(ml|cc|l|lt|g|kg|gr|un|uds|unidades)\b",
    re.IGNORECASE,
)

_UNIT_ALIASES = {"lt": "l", "gr": "g", "uds": "un", "unidades": "un"}


def parse_presentation(raw: str | None) -> tuple[Decimal | None, str | None]:
    """Extrae (cantidad, unidad) de la presentacion cruda."""
    if not raw:
        return None, None
    match = _PRESENTATION_RE.search(raw)
    if not match:
        return None, None
    value, unit = match.group(1), match.group(2).lower()
    try:
        quantity = Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None, None
    return quantity, _UNIT_ALIASES.get(unit, unit)


def _es_cambio(
    previo: tuple[Decimal, str],
    actual: tuple[Decimal, str],
) -> bool:
    """Alerta si cambia la unidad, o si la cantidad BAJA en la misma
    unidad. Un aumento de gramaje no es reduflacion."""
    (qty_a, unit_a), (qty_b, unit_b) = previo, actual
    if unit_a != unit_b:
        return True
    return qty_b < qty_a


def _puntaje_reduccion(
    previo: tuple[Decimal, str],
    actual: tuple[Decimal, str],
) -> Decimal | None:
    """% de reduccion si la unidad es la misma y hay bajada de cantidad."""
    (qty_a, unit_a), (qty_b, unit_b) = previo, actual
    if unit_a != unit_b or qty_a == 0 or qty_b >= qty_a:
        return None
    return (((qty_a - qty_b) / qty_a) * 100).quantize(Decimal("0.01"))


def _alerta_abierta_existe(
    db: Session,
    store_product_id: int,
    observed_at: datetime,
) -> bool:
    existente = db.scalars(
        select(AnomalyAlert).where(
            AnomalyAlert.alert_type == "shrinkflation",
            AnomalyAlert.status == "open",
            AnomalyAlert.store_product_id == store_product_id,
        ),
    ).first()
    if existente is None:
        return False
    return existente.details.get("observed_at") == observed_at.isoformat()


def detect_shrinkflation(
    db: Session,
    store_product_id: int | None = None,
) -> list[AnomalyAlert]:
    """Evalua observaciones consecutivas y persiste alertas nuevas."""
    query = select(StoreProduct).where(StoreProduct.producto_id.is_not(None))
    if store_product_id is not None:
        query = query.where(StoreProduct.id == store_product_id)

    store_products = list(db.scalars(query.order_by(StoreProduct.id)))
    if store_product_id is not None and not store_products:
        raise NotFoundError(f"store_product {store_product_id} no encontrado")

    creadas: list[AnomalyAlert] = []
    for sp in store_products:
        filas = list(
            db.scalars(
                select(PrecioHistorico)
                .where(
                    PrecioHistorico.tienda_id == sp.tienda_id,
                    PrecioHistorico.producto_id == sp.producto_id,
                    PrecioHistorico.raw_presentation.is_not(None),
                )
                .order_by(
                    PrecioHistorico.timestamp.asc(),
                    PrecioHistorico.id.asc(),
                ),
            ),
        )

        previa: tuple[datetime, tuple[Decimal, str]] | None = None
        for fila in filas:
            qty, unit = parse_presentation(fila.raw_presentation)
            if qty is None or unit is None:
                previa = None  # rompe la cadena: no se puede comparar
                continue
            actual: tuple[Decimal, str] = (qty, unit)

            if previa is not None and _es_cambio(previa[1], actual):
                _ts_prev, prev_tuple = previa
                if not _alerta_abierta_existe(db, sp.id, fila.timestamp):
                    score = _puntaje_reduccion(prev_tuple, actual)
                    alerta = AnomalyAlert(
                        alert_type="shrinkflation",
                        producto_id=sp.producto_id,
                        store_product_id=sp.id,
                        tienda_id=sp.tienda_id,
                        score=None
                        if score is None
                        else (score / 100).quantize(Decimal("0.0001")),
                        severity="medium"
                        if score is None or score < 20
                        else "high",
                        status="open",
                        details={
                            "prev_presentation": f"{prev_tuple[0]} {prev_tuple[1]}",
                            "curr_presentation": f"{qty} {unit}",
                            "prev_qty": str(prev_tuple[0]),
                            "curr_qty": str(qty),
                            "prev_unit": prev_tuple[1],
                            "curr_unit": unit,
                            "reduction_pct": None
                            if score is None
                            else str(score),
                            "observed_at": fila.timestamp.isoformat(),
                        },
                    )
                    db.add(alerta)
                    creadas.append(alerta)

            previa = (fila.timestamp, actual)

    if creadas:
        db.commit()
        for alerta in creadas:
            db.refresh(alerta)
    return creadas
