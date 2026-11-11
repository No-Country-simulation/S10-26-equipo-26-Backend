"""Tests de modelos 0002: store_products y anomaly_alerts (decisiones #7/#8)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.anomaly_alert import AnomalyAlert
from src.models.categoria import Categoria
from src.models.producto_canonico import ProductoCanonico
from src.models.store_product import StoreProduct
from src.models.tienda import Tienda


def _seed_catalogo(session):
    categoria = Categoria(nombre="Alimentos y Bebidas")
    tienda = Tienda(nombre="Coto", url_base="https://www.cototesting.com.ar")
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L", marca="Coca Cola")
    session.add_all([categoria, tienda, producto])
    session.flush()
    return tienda, producto


def test_store_product_duplicado_rechazado(db_session) -> None:
    tienda, producto = _seed_catalogo(db_session)
    db_session.add(
        StoreProduct(
            producto_id=producto.id,
            tienda_id=tienda.id,
            external_id="EXT-1",
            nombre_crudo="COCA COLA 2 LT",
        )
    )
    db_session.commit()

    db_session.add(
        StoreProduct(
            producto_id=producto.id,
            tienda_id=tienda.id,
            external_id="EXT-1",
            nombre_crudo="COCA COLA 2 LITROS",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_store_product_unico_mismo_external_id_en_otra_tienda_ok(db_session) -> None:
    tienda, producto = _seed_catalogo(db_session)
    otra = Tienda(nombre="Carrefour")
    db_session.add(otra)
    db_session.flush()

    db_session.add_all(
        [
            StoreProduct(
                producto_id=producto.id,
                tienda_id=tienda.id,
                external_id="EXT-1",
                nombre_crudo="COCA COLA 2 LT",
            ),
            StoreProduct(
                producto_id=producto.id,
                tienda_id=otra.id,
                external_id="EXT-1",
                nombre_crudo="Coca-Cola 2 litros",
            ),
        ]
    )
    db_session.commit()
    assert db_session.query(StoreProduct).count() == 2


def test_store_product_requiere_campos_obligatorios(db_session) -> None:
    tienda, producto = _seed_catalogo(db_session)
    db_session.add(
        StoreProduct(
            producto_id=producto.id,
            tienda_id=tienda.id,
            external_id="EXT-2",
            nombre_crudo=None,  # type: ignore[arg-type]
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_anomaly_alert_defaults_open_medium(db_session) -> None:
    alerta = AnomalyAlert(alert_type="shrinkflation")
    db_session.add(alerta)
    db_session.commit()

    guardada = db_session.query(AnomalyAlert).one()
    assert guardada.status == "open"
    assert guardada.severity == "medium"
    assert guardada.details == {}
    assert guardada.created_at is not None


def test_anomaly_alert_tipo_invalido_rechazado(db_session) -> None:
    db_session.add(AnomalyAlert(alert_type="fake_type"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_anomaly_alert_status_invalido_rechazado(db_session) -> None:
    db_session.add(AnomalyAlert(alert_type="shrinkflation", status="deleted"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_anomaly_alert_campos_numericos_y_revision(db_session) -> None:
    ahora = datetime.now(UTC)
    alerta = AnomalyAlert(
        alert_type="outpace_devaluation",
        score=Decimal("10.5000"),
        severity="high",
        details={"price_variation": 30, "fx_variation": 20},
        reviewed_at=ahora,
    )
    db_session.add(alerta)
    db_session.commit()

    guardada = db_session.query(AnomalyAlert).one()
    assert guardada.score == Decimal("10.5000")
    assert guardada.severity == "high"
    assert guardada.details["price_variation"] == 30
    assert guardada.reviewed_at is not None
