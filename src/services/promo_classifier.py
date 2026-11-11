"""Clasificacion promo vs regular derivada en lectura (HU 2.2).

Regla de negocio acordada: si hay precio tachado y descuento >= umbral (10%)
=> promo. El badge `en_oferta` del sitio tambien marca promo (senal del
e-commerce, conservadora para no contar una oferta como baja real).

No se persiste nada: `is_promotion`/`price_regular` se calculan al leer.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

DEFAULT_DISCOUNT_THRESHOLD = Decimal("0.10")


@dataclass(frozen=True)
class PromoClassification:
    is_promotion: bool
    price_regular: Decimal
    discount_pct: Decimal


def _to_decimal(value: Decimal | float | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def classify(
    precio: Decimal | float | str,
    precio_tachado: Decimal | float | str | None = None,
    en_oferta: bool | None = False,
    threshold: Decimal | float | str = DEFAULT_DISCOUNT_THRESHOLD,
) -> PromoClassification:
    """Clasifica una observacion de precio.

    - `precio` precio actual observado (siempre requerido).
    - `precio_tachado` precio "antes" publicado por el sitio.
    - `en_oferta` badge de oferta del sitio.
    - `threshold` descuento minimo (default 0.10 = 10%).
    """
    actual = _to_decimal(precio)
    if actual is None or actual <= 0:
        raise ValueError("precio debe ser numerico positivo")

    tachado = _to_decimal(precio_tachado)
    umbral = _to_decimal(threshold)
    if umbral is None or umbral < 0:
        raise ValueError("threshold invalido")

    discount_pct = Decimal(0)
    por_tachado = False

    if tachado is not None and tachado > 0 and tachado > actual:
        discount_pct = ((tachado - actual) / tachado).quantize(
            Decimal("0.0001")
        )
        por_tachado = discount_pct >= umbral

    is_promotion = bool(en_oferta) or por_tachado

    if tachado is not None and tachado > actual:
        price_regular = tachado
    else:
        price_regular = actual

    return PromoClassification(
        is_promotion=is_promotion,
        price_regular=price_regular,
        discount_pct=discount_pct,
    )
