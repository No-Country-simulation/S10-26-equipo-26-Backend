"""Indice de inflacion base sin promos (HU 2.3, decision #4).

Metodo (documentado en README del Backend):
1. Excluir observaciones `en_oferta = true` o clasificadas como promo
   (precio_tachado con descuento >= 10%, ver promo_classifier).
2. Por producto: mediana movil de `window_days` (7) sobre precios
   regulares. La ventana se promedia por dia (mediana del dia) y luego
   mediana de los ultimos N dias con datos.
3. Por producto: ratio R_p(t) = mediana(t) / mediana(t0), donde t0 es
   la primera fecha con mediana dentro del rango.
4. Indice(t) = 100 * media de R_p(t) sobre los productos con mediana
   en t. Base 100 en t0.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.services.promo_classifier import classify

DEFAULT_WINDOW_DAYS = 7
BASE_INDEX = Decimal(100)

METHOD_DESCRIPTION = (
    "mediana movil 7d de precios regulares por producto "
    "(excluye en_oferta y descuentos >= 10%), "
    "media de ratios por categoria, base 100"
)


@dataclass(frozen=True)
class InflationPoint:
    date: date
    index: Decimal


@dataclass(frozen=True)
class InflationResult:
    series: list[InflationPoint]
    base: Decimal
    method: str
    excluded_promos: int
    products_count: int


def _daily_median(precios: list[Decimal]) -> Decimal:
    return Decimal(str(median(precios)))


def window_median(
    daily: dict[date, Decimal],
    day: date,
    window_days: int,
) -> Decimal | None:
    """Mediana de los valores diarios en [day - window_days + 1, day]."""
    valores = [
        daily[day - timedelta(days=offset)]
        for offset in range(window_days)
        if (day - timedelta(days=offset)) in daily
    ]
    if not valores:
        return None
    return Decimal(str(median(valores)))


def daily_regular_prices(
    db: Session,
    category_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    currency: str = "local",
) -> tuple[dict[int | None, dict[date, Decimal]], int]:
    """Precios regulares por producto y dia (mediana del dia).

    Devuelve (mapa producto_id -> {fecha: mediana}, excluidas_promo).
    Reutilizado por el indice de inflacion y por el motor de alertas.
    """
    if currency not in ("local", "usd"):
        raise ValueError("currency debe ser 'local' o 'usd'")

    stmt = select(PrecioHistorico, ProductoCanonico).join(
        ProductoCanonico,
        PrecioHistorico.producto_id == ProductoCanonico.id,
        isouter=True,
    )
    if category_id is not None:
        stmt = stmt.where(ProductoCanonico.categoria_id == category_id)
    if start is not None:
        stmt = stmt.where(
            PrecioHistorico.timestamp
            >= datetime.combine(start, time.min, tzinfo=UTC),
        )
    if end is not None:
        stmt = stmt.where(
            PrecioHistorico.timestamp
            < datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC),
        )

    rows = db.execute(stmt).all()

    excluded_promos = 0
    bruto: dict[int | None, dict[date, list[Decimal]]] = defaultdict(
        lambda: defaultdict(list),
    )
    campo = "precio_usd" if currency == "usd" else "precio_local"

    for precio_row, _producto in rows:
        if precio_row.en_oferta:
            excluded_promos += 1
            continue
        clasificacion = classify(
            precio=precio_row.precio_local,
            precio_tachado=precio_row.precio_tachado,
            en_oferta=precio_row.en_oferta,
        )
        if clasificacion.is_promotion:
            excluded_promos += 1
            continue
        valor = getattr(precio_row, campo)
        if valor is None or valor == 0:
            continue
        dia = precio_row.timestamp.date()
        bruto[precio_row.producto_id][dia].append(valor)

    daily_por_producto: dict[int | None, dict[date, Decimal]] = {
        producto_id: {
            dia: _daily_median(valores)
            for dia, valores in dias.items()
        }
        for producto_id, dias in bruto.items()
    }
    return daily_por_producto, excluded_promos


def compute_inflation(
    db: Session,
    category_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    currency: str = "local",
) -> InflationResult:
    """Serie de indice. `currency='local'` usa precio_local; `'usd'` usa
    precio_usd persistido (HU 3.3). La clasificacion promo siempre se
    evalua sobre el precio local (badge/tachado)."""
    daily_por_producto, excluded_promos = daily_regular_prices(
        db,
        category_id=category_id,
        start=start,
        end=end,
        currency=currency,
    )

    if not daily_por_producto:
        return InflationResult(
            series=[],
            base=BASE_INDEX,
            method=METHOD_DESCRIPTION,
            excluded_promos=excluded_promos,
            products_count=0,
        )

    todas_fechas = sorted(
        {dia for dias in daily_por_producto.values() for dia in dias}
    )

    medias_por_producto: dict[int | None, dict[date, Decimal]] = {}

    for producto_id, daily in daily_por_producto.items():
        ratios: dict[date, Decimal] = {}
        base: Decimal | None = None
        for dia in todas_fechas:
            valor = window_median(daily, dia, window_days)
            if valor is None or valor == 0:
                continue
            if base is None:
                base = valor
            if base is not None:
                ratios[dia] = valor / base
        if base is not None:
            medias_por_producto[producto_id] = ratios

    series: list[InflationPoint] = []
    for dia in todas_fechas:
        valores = [
            ratios[dia]
            for ratios in medias_por_producto.values()
            if dia in ratios
        ]
        if not valores:
            continue
        total = sum(valores, Decimal(0))
        promedio = total / len(valores)
        series.append(
            InflationPoint(
                date=dia,
                index=(BASE_INDEX * promedio).quantize(Decimal("0.01")),
            ),
        )

    return InflationResult(
        series=series,
        base=BASE_INDEX,
        method=METHOD_DESCRIPTION,
        excluded_promos=excluded_promos,
        products_count=len(medias_por_producto),
    )
