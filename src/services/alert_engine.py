"""Motor de alertas por devaluacion (HU 3.5).

Para cada producto con precios regulares en el rango:
- `price_var` = (ultima mediana movil / base) - 1 (misma exclusion de
  promos que el indice de inflacion).
- `fx_var` = variacion de la cotizacion oficial as-of en el rango.
- `gap` = price_var - fx_var. Si `gap > umbral` se crea una alerta
  `outpace_devaluation` con `score = gap`.

Severidad: gap >= 0.20 => high; >= 0.10 => medium; > umbral => low.
Idempotente: no duplica alertas abiertas del mismo producto y rango.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analytics.devaluation import fx_variation
from src.analytics.inflation import daily_regular_prices, window_median
from src.core.exceptions import ValidationError
from src.models.anomaly_alert import AnomalyAlert

DEFAULT_THRESHOLD = Decimal(0)
SEVERITY_HIGH = Decimal("0.20")
SEVERITY_MEDIUM = Decimal("0.10")


def severity_for(gap: Decimal) -> str:
    if gap >= SEVERITY_HIGH:
        return "high"
    if gap >= SEVERITY_MEDIUM:
        return "medium"
    return "low"


def _product_price_variation(
    daily: dict[date, Decimal],
    fechas: list[date],
    window_days: int,
) -> tuple[Decimal, Decimal] | None:
    """(price_var, base) o None si no hay >= 2 puntos en la ventana."""
    base: Decimal | None = None
    ultima: Decimal | None = None
    for dia in fechas:
        valor = window_median(daily, dia, window_days)
        if valor is None or valor == 0:
            continue
        if base is None:
            base = valor
        ultima = valor
    if base is None or ultima is None or base == 0:
        return None
    return (ultima - base) / base, base


def _alerta_abierta_existe(
    db: Session,
    producto_id: int | None,
    start: date,
    end: date,
) -> bool:
    existente = db.scalars(
        select(AnomalyAlert).where(
            AnomalyAlert.alert_type == "outpace_devaluation",
            AnomalyAlert.status == "open",
            AnomalyAlert.producto_id == producto_id,
        ),
    ).first()
    if existente is None:
        return False
    return (
        existente.details.get("start") == start.isoformat()
        and existente.details.get("end") == end.isoformat()
    )


def evaluate_outpace_devaluation(
    db: Session,
    start: date,
    end: date,
    window_days: int = 1,
    threshold: Decimal = DEFAULT_THRESHOLD,
) -> list[AnomalyAlert]:
    """Evalua todos los productos del rango y persiste las alertas."""
    if start > end:
        raise ValidationError("start no puede ser posterior a end")

    daily_por_producto, _excluded = daily_regular_prices(
        db,
        start=start,
        end=end,
    )
    if not daily_por_producto:
        return []

    _fx_start, _fx_end, fx_var = fx_variation(db, start, end)

    todas_fechas = sorted(
        {dia for dias in daily_por_producto.values() for dia in dias}
    )

    creadas: list[AnomalyAlert] = []
    for producto_id, daily in daily_por_producto.items():
        variacion = _product_price_variation(daily, todas_fechas, window_days)
        if variacion is None:
            continue
        price_var, _base = variacion
        gap = (price_var - fx_var).quantize(Decimal("0.0001"))
        if gap <= threshold:
            continue
        if _alerta_abierta_existe(db, producto_id, start, end):
            continue

        alerta = AnomalyAlert(
            alert_type="outpace_devaluation",
            producto_id=producto_id,
            score=gap,
            severity=severity_for(gap),
            status="open",
            details={
                "start": start.isoformat(),
                "end": end.isoformat(),
                "price_variation": str(price_var.quantize(Decimal("0.0001"))),
                "fx_variation": str(fx_var),
                "gap": str(gap),
                "window_days": window_days,
            },
        )
        db.add(alerta)
        creadas.append(alerta)

    if creadas:
        db.commit()
        for alerta in creadas:
            db.refresh(alerta)
    return creadas
