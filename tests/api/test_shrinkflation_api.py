"""Integracion: deteccion de reduflacion (HU 2.4)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.models.store_product import StoreProduct
from src.models.tienda import Tienda

T0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def seed_reduflacion(db_session):
    tienda = Tienda(nombre="Coto")
    producto = ProductoCanonico(nombre_universal="Yerba 500 g")
    db_session.add_all([tienda, producto])
    db_session.flush()
    sp = StoreProduct(
        tienda_id=tienda.id,
        producto_id=producto.id,
        external_id="EXT-1",
        nombre_crudo="Yerba Mate 500 g",
    )
    db_session.add(sp)
    db_session.flush()

    for i, pres in enumerate(["500 g", "500 g", "400 g"]):
        db_session.add(
            PrecioHistorico(
                timestamp=T0 + timedelta(days=i),
                producto_id=producto.id,
                tienda_id=tienda.id,
                precio_local="1000.00",
                tipo_cambio_usado="1000.0000",
                precio_usd="1.00",
                raw_presentation=pres,
            )
        )
    db_session.commit()
    return {"store_product": sp, "tienda": tienda}


def test_detect_crea_alerta(api_client, seed_reduflacion) -> None:
    response = api_client.post(
        "/api/v1/alerts/detect-shrinkflation",
        params={"store_product_id": seed_reduflacion["store_product"].id},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["alert_type"] == "shrinkflation"
    assert body[0]["details"]["prev_presentation"] == "500 g"
    assert body[0]["details"]["curr_presentation"] == "400 g"
    assert Decimal(body[0]["score"]) == Decimal("0.2000")

    # idempotente
    segunda = api_client.post(
        "/api/v1/alerts/detect-shrinkflation",
        params={"store_product_id": seed_reduflacion["store_product"].id},
    )
    assert segunda.json() == []


def test_detect_global(api_client, seed_reduflacion) -> None:
    response = api_client.post("/api/v1/alerts/detect-shrinkflation")
    assert response.status_code == 201
    assert len(response.json()) == 1


def test_alerta_visible_en_list_filtrada_por_tipo(
    api_client,
    seed_reduflacion,
) -> None:
    api_client.post("/api/v1/alerts/detect-shrinkflation")

    response = api_client.get(
        "/api/v1/alerts",
        params={"type": "shrinkflation", "status": "open"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_detect_store_product_inexistente_404(api_client) -> None:
    response = api_client.post(
        "/api/v1/alerts/detect-shrinkflation",
        params={"store_product_id": 99999},
    )
    assert response.status_code == 404


def test_detect_store_product_id_invalido_422(api_client) -> None:
    response = api_client.post(
        "/api/v1/alerts/detect-shrinkflation",
        params={"store_product_id": 0},
    )
    assert response.status_code == 422
