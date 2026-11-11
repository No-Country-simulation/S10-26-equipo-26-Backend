"""Tests de unidad: motor de alertas outpace_devaluation (HU 3.5)."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from src.core.exceptions import NotFoundError, ValidationError
from src.models.anomaly_alert import AnomalyAlert
from src.models.historial_divisa import HistorialDivisa
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.services import alert_engine

DIA1 = date(2026, 10, 1)
DIA7 = date(2026, 10, 7)


def _seed(db, precio_final: str) -> ProductoCanonico:
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    db.add(producto)
    db.flush()

    for dia, precio in ((DIA1, "100.00"), (DIA7, precio_final)):
        db.add(
            PrecioHistorico(
                timestamp=datetime.combine(dia, time(10, 0), tzinfo=UTC),
                producto_id=producto.id,
                precio_local=precio,
                tipo_cambio_usado="1000.0000",
                precio_usd=Decimal(precio) / Decimal(1000),
            )
        )

    db.add_all(
        [
            HistorialDivisa(
                timestamp=datetime.combine(DIA1, time(0, 0), tzinfo=UTC),
                tipo_cambio_oficial="1000.0000",
                tipo_cambio_paralelo="1020.0000",
            ),
            HistorialDivisa(
                timestamp=datetime.combine(DIA7, time(12, 0), tzinfo=UTC),
                tipo_cambio_oficial="1200.0000",
                tipo_cambio_paralelo="1250.0000",
            ),
        ]
    )
    db.commit()
    return producto


def test_precio_30_fx_20_genera_alerta(db_session) -> None:
    """DOD HU 3.5: producto sube 30%, FX 20% => alerta."""
    producto = _seed(db_session, "130.00")

    alertas = alert_engine.evaluate_outpace_devaluation(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.alert_type == "outpace_devaluation"
    assert alerta.producto_id == producto.id
    assert alerta.score == Decimal("0.1000")
    assert alerta.severity == "medium"
    assert alerta.status == "open"
    assert alerta.details["price_variation"] == "0.3000"
    assert alerta.details["fx_variation"] == "0.2000"
    assert alerta.details["start"] == DIA1.isoformat()
    assert alerta.created_at is not None

    assert db_session.query(AnomalyAlert).count() == 1


def test_precio_bajo_no_genera_alerta(db_session) -> None:
    _seed(db_session, "110.00")  # +10% contra FX +20% => gap negativo

    alertas = alert_engine.evaluate_outpace_devaluation(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert alertas == []
    assert db_session.query(AnomalyAlert).count() == 0


def test_severidad_low(db_session) -> None:
    _seed(db_session, "125.00")  # +25% - 20% => gap 0.05

    alertas = alert_engine.evaluate_outpace_devaluation(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert len(alertas) == 1
    assert alertas[0].severity == "low"
    assert alertas[0].score == Decimal("0.0500")


def test_severidad_high(db_session) -> None:
    _seed(db_session, "160.00")  # +60% - 20% => gap 0.40

    alertas = alert_engine.evaluate_outpace_devaluation(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert len(alertas) == 1
    assert alertas[0].severity == "high"
    assert alertas[0].score == Decimal("0.4000")


def test_idempotente_no_duplica_alertas_abiertas(db_session) -> None:
    _seed(db_session, "130.00")

    primera = alert_engine.evaluate_outpace_devaluation(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )
    segunda = alert_engine.evaluate_outpace_devaluation(
        db_session,
        start=DIA1,
        end=DIA7,
        window_days=1,
    )

    assert len(primera) == 1
    assert segunda == []
    assert db_session.query(AnomalyAlert).count() == 1


def test_umbral_configurable(db_session) -> None:
    _seed(db_session, "125.00")  # gap 0.05

    assert (
        alert_engine.evaluate_outpace_devaluation(
            db_session,
            start=DIA1,
            end=DIA7,
            window_days=1,
            threshold=Decimal("0.10"),
        )
        == []
    )


def test_sin_cotizaciones_lanza_404(db_session) -> None:
    producto = ProductoCanonico(nombre_universal="X")
    db_session.add(producto)
    db_session.flush()
    db_session.add(
        PrecioHistorico(
            timestamp=datetime.combine(DIA1, time(10, 0), tzinfo=UTC),
            producto_id=producto.id,
            precio_local="100.00",
            tipo_cambio_usado="1000.0000",
            precio_usd="0.10",
        )
    )
    db_session.commit()

    with pytest.raises(NotFoundError, match="cotizaciones"):
        alert_engine.evaluate_outpace_devaluation(
            db_session,
            start=DIA1,
            end=DIA7,
        )


def test_rango_invalido_lanza_validation_error(db_session) -> None:
    with pytest.raises(ValidationError, match="posterior"):
        alert_engine.evaluate_outpace_devaluation(
            db_session,
            start=DIA7,
            end=DIA1,
        )


def test_sin_precios_devuelve_vacio(db_session) -> None:
    assert (
        alert_engine.evaluate_outpace_devaluation(
            db_session,
            start=DIA1,
            end=DIA7,
        )
        == []
    )
