"""Variacion de precios vs devaluacion (HU 3.4).

- `price_variation`: variacion del indice de inflacion en el rango
  (ultimo indice / primero - 1), sobre precios regulares.
- `fx_variation`: (fx_fin - fx_ini) / fx_ini con la cotizacion oficial
  as-of del inicio y del fin del rango (HU 3.2).
- `gap` = price_variation - fx_variation. Positivo => los precios
  superaron a la devaluacion.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session

from src.analytics.inflation import compute_inflation
from src.core.exceptions import NotFoundError, ValidationError
from src.services.fx_service import get_rate_as_of

ZERO = Decimal(0)


@dataclass(frozen=True)
class DevaluationGap:
    start: date
    end: date
    price_variation: Decimal
    fx_variation: Decimal
    gap: Decimal
    fx_start: Decimal
    fx_end: Decimal


def compute_devaluation_gap(
    db: Session,
    start: date,
    end: date,
    category_id: int | None = None,
    window_days: int = 7,
) -> DevaluationGap:
    if start > end:
        raise ValidationError("start no puede ser posterior a end")

    inflacion = compute_inflation(
        db,
        category_id=category_id,
        start=start,
        end=end,
        window_days=window_days,
    )
    if len(inflacion.series) < 2:
        raise NotFoundError("no hay suficientes precios en el rango")

    primero = inflacion.series[0].index
    ultimo = inflacion.series[-1].index
    if primero == 0:
        raise NotFoundError("indice base invalido")
    price_variation = (ultimo - primero) / primero

    fx_ini = get_rate_as_of(
        db,
        datetime.combine(start, time.min, tzinfo=UTC),
    ).tipo_cambio_oficial
    fx_fin = get_rate_as_of(
        db,
        datetime.combine(end, time.max, tzinfo=UTC),
    ).tipo_cambio_oficial

    if fx_ini == 0:
        raise NotFoundError("tipo de cambio inicial invalido")
    fx_variation = (fx_fin - fx_ini) / fx_ini

    return DevaluationGap(
        start=start,
        end=end,
        price_variation=price_variation.quantize(Decimal("0.0001")),
        fx_variation=fx_variation.quantize(Decimal("0.0001")),
        gap=(price_variation - fx_variation).quantize(Decimal("0.0001")),
        fx_start=fx_ini,
        fx_end=fx_fin,
    )
