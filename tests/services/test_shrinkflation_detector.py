"""Tests de unidad: shrinkflation_detector (HU 2.4) + paridad con Data."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.core.exceptions import NotFoundError
from src.models.anomaly_alert import AnomalyAlert
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.models.store_product import StoreProduct
from src.models.tienda import Tienda
from src.services.shrinkflation_detector import (
    detect_shrinkflation,
    parse_presentation,
)

# --- paridad con src/normalizers/presentation.py del repo Data ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("500 g", (Decimal(500), "g")),
        ("1 kg", (Decimal(1), "kg")),
        ("Pack x 2 unidades", (Decimal(2), "un")),
        ("750 ml", (Decimal(750), "ml")),
        ("2 Lt", (Decimal(2), "l")),
        ("sin presentacion", (None, None)),
        (None, (None, None)),
        ("", (None, None)),
        ("Coca Cola", (None, None)),
    ],
)
def test_parse_presentation_paridad(raw, expected) -> None:
    assert parse_presentation(raw) == expected


T0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)


def _seed(db, presentaciones: list[str], dia_base: datetime = T0):
    tienda = Tienda(nombre="Coto")
    producto = ProductoCanonico(nombre_universal="Yerba 500 g")
    db.add_all([tienda, producto])
    db.flush()
    sp = StoreProduct(
        tienda_id=tienda.id,
        producto_id=producto.id,
        external_id="EXT-1",
        nombre_crudo="Yerba Mate 500 g",
    )
    db.add(sp)
    db.flush()

    for i, pres in enumerate(presentaciones):
        db.add(
            PrecioHistorico(
                timestamp=dia_base + timedelta(days=i),
                producto_id=producto.id,
                tienda_id=tienda.id,
                precio_local="1000.00",
                tipo_cambio_usado="1000.0000",
                precio_usd="1.00",
                raw_presentation=pres,
            )
        )
    db.commit()
    return sp


def test_cambio_500g_a_400g_genera_alerta(db_session) -> None:
    """DOD HU 2.4: secuencia sintetica 500 g -> 400 g."""
    sp = _seed(db_session, ["500 g", "500 g", "400 g"])

    alertas = detect_shrinkflation(db_session, store_product_id=sp.id)

    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.alert_type == "shrinkflation"
    assert alerta.store_product_id == sp.id
    assert alerta.status == "open"
    assert alerta.details["prev_presentation"] == "500 g"
    assert alerta.details["curr_presentation"] == "400 g"
    assert alerta.details["reduction_pct"] == "20.00"
    assert alerta.score == Decimal("0.2000")
    assert alerta.severity == "high"  # reduccion >= 20%
    assert db_session.query(AnomalyAlert).count() == 1


def test_presentacion_igual_no_genera_alerta(db_session) -> None:
    sp = _seed(db_session, ["500 g", "500 g", "500 g"])

    assert detect_shrinkflation(db_session, store_product_id=sp.id) == []
    assert db_session.query(AnomalyAlert).count() == 0


def test_aumento_de_gramaje_no_genera_alerta(db_session) -> None:
    sp = _seed(db_session, ["400 g", "500 g"])

    assert detect_shrinkflation(db_session, store_product_id=sp.id) == []


def test_cambio_de_unidad_genera_alerta(db_session) -> None:
    sp = _seed(db_session, ["500 g", "500 ml"])

    alertas = detect_shrinkflation(db_session, store_product_id=sp.id)

    assert len(alertas) == 1
    assert alertas[0].details["prev_unit"] == "g"
    assert alertas[0].details["curr_unit"] == "ml"
    assert alertas[0].score is None
    assert alertas[0].severity == "medium"


def test_presentacion_no_parseable_rompe_la_cadena(db_session) -> None:
    sp = _seed(db_session, ["500 g", "sin datos", "400 g"])

    assert detect_shrinkflation(db_session, store_product_id=sp.id) == []


def test_idempotente_no_duplica(db_session) -> None:
    sp = _seed(db_session, ["500 g", "400 g"])

    primera = detect_shrinkflation(db_session, store_product_id=sp.id)
    segunda = detect_shrinkflation(db_session, store_product_id=sp.id)

    assert len(primera) == 1
    assert segunda == []
    assert db_session.query(AnomalyAlert).count() == 1


def test_dos_reducciones_generan_dos_alertas(db_session) -> None:
    sp = _seed(db_session, ["500 g", "400 g", "300 g"])

    alertas = detect_shrinkflation(db_session, store_product_id=sp.id)

    assert len(alertas) == 2
    assert {a.details["curr_qty"] for a in alertas} == {"400", "300"}


def test_store_product_inexistente_lanza_404(db_session) -> None:
    with pytest.raises(NotFoundError, match="store_product"):
        detect_shrinkflation(db_session, store_product_id=99999)


def test_store_product_sin_match_no_se_evalua(db_session) -> None:
    sp = _seed(db_session, ["500 g", "400 g"])
    sp.producto_id = None
    db_session.commit()

    with pytest.raises(NotFoundError):
        detect_shrinkflation(db_session, store_product_id=sp.id)


def test_scan_global_sin_filtro(db_session) -> None:
    _seed(db_session, ["500 g", "400 g"])

    alertas = detect_shrinkflation(db_session)

    assert len(alertas) == 1
    assert alertas[0].alert_type == "shrinkflation"
