"""Tests de unidad: devaluation-gap (HU 3.4) y precio en USD (HU 3.4)."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from src.analytics.devaluation import compute_devaluation_gap
from src.analytics.inflation import compute_inflation
from src.core.exceptions import NotFoundError, ValidationError
from src.models.historial_divisa import HistorialDivisa
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico

DIA1 = date(2026, 10, 1)
DIA7 = date(2026, 10, 7)


def _seed_producto(db) -> ProductoCanonico:
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    db.add(producto)
    db.flush()
    return producto


def _seed_precio(db, producto_id: int, dia: date, precio_local: str, precio_usd: str) -> None:
    db.add(
        PrecioHistorico(
            timestamp=datetime.combine(dia, time(10, 0), tzinfo=UTC),
            producto_id=producto_id,
            precio_local=precio_local,
            tipo_cambio_usado="1000.0000",
            precio_usd=precio_usd,
        )
    )


def _seed_fx(db, dia: date, oficial: str, hora: time = time(0, 0)) -> None:
    db.add(
        HistorialDivisa(
            timestamp=datetime.combine(dia, hora, tzinfo=UTC),
            tipo_cambio_oficial=oficial,
            tipo_cambio_paralelo=oficial,
        )
    )


def test_precio_sube_menos_que_la_devaluacion_gap_negativo(db_session) -> None:
    producto = _seed_producto(db_session)
    _seed_precio(db_session, producto.id, DIA1, "100.00", "0.10")
    _seed_precio(db_session, producto.id, DIA7, "110.00", "0.11")
    _seed_fx(db_session, DIA1, "1000.0000")
    _seed_fx(db_session, DIA7, "1200.0000", hora=time(12, 0))
    db_session.commit()

    gap = compute_devaluation_gap(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert gap.price_variation == Decimal("0.1000")
    assert gap.fx_variation == Decimal("0.2000")
    assert gap.gap == Decimal("-0.1000")
    assert gap.fx_start == Decimal("1000.0000")
    assert gap.fx_end == Decimal("1200.0000")


def test_precio_supera_devaluacion_gap_positivo(db_session) -> None:
    """Escenario HU 3.5: precio +30%, FX +20% => gap positivo."""
    producto = _seed_producto(db_session)
    _seed_precio(db_session, producto.id, DIA1, "100.00", "0.10")
    _seed_precio(db_session, producto.id, DIA7, "130.00", "0.13")
    _seed_fx(db_session, DIA1, "1000.0000")
    _seed_fx(db_session, DIA7, "1200.0000", hora=time(12, 0))
    db_session.commit()

    gap = compute_devaluation_gap(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert gap.price_variation == Decimal("0.3000")
    assert gap.fx_variation == Decimal("0.2000")
    assert gap.gap == Decimal("0.1000")


def test_sin_precios_suficientes_lanza_404(db_session) -> None:
    producto = _seed_producto(db_session)
    _seed_precio(db_session, producto.id, DIA1, "100.00", "0.10")
    _seed_fx(db_session, DIA1, "1000.0000")
    db_session.commit()

    with pytest.raises(NotFoundError, match="precios"):
        compute_devaluation_gap(db_session, start=DIA1, end=DIA7, window_days=1)


def test_sin_cotizaciones_lanza_404(db_session) -> None:
    producto = _seed_producto(db_session)
    _seed_precio(db_session, producto.id, DIA1, "100.00", "0.10")
    _seed_precio(db_session, producto.id, DIA7, "110.00", "0.11")
    db_session.commit()

    with pytest.raises(NotFoundError, match="cotizaciones"):
        compute_devaluation_gap(db_session, start=DIA1, end=DIA7, window_days=1)


def test_rango_invalido_lanza_validation_error(db_session) -> None:
    with pytest.raises(ValidationError, match="posterior"):
        compute_devaluation_gap(db_session, start=DIA7, end=DIA1)


def test_inflation_currency_usd_refleja_fx(db_session) -> None:
    """Precio local plano, pero el USD baja => indice en USD cae."""
    producto = _seed_producto(db_session)
    _seed_precio(db_session, producto.id, DIA1, "1000.00", "1.00")
    _seed_precio(db_session, producto.id, DIA7, "1000.00", "0.80")
    db_session.commit()

    local = compute_inflation(db_session, window_days=1, currency="local")
    usd = compute_inflation(db_session, window_days=1, currency="usd")

    assert local.series[-1].index == Decimal("100.00")
    assert usd.series[-1].index == Decimal("80.00")


def test_inflation_currency_invalido(db_session) -> None:
    with pytest.raises(ValueError, match="currency"):
        compute_inflation(db_session, currency="eur")
