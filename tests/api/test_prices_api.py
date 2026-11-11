"""Integracion: GET /api/v1/prices/history (HU 3.3 + clasificacion HU 2.2)."""

from datetime import UTC, datetime

import pytest

from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.models.tienda import Tienda

DIA1 = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
DIA2 = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)


@pytest.fixture
def seed_precios(db_session):
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    tienda = Tienda(nombre="Coto")
    db_session.add_all([producto, tienda])
    db_session.flush()

    db_session.add_all(
        [
            PrecioHistorico(
                timestamp=DIA1,
                producto_id=producto.id,
                tienda_id=tienda.id,
                precio_local="1000.00",
                tipo_cambio_usado="1000.0000",
                precio_usd="1.00",
            ),
            PrecioHistorico(
                timestamp=DIA2,
                producto_id=producto.id,
                tienda_id=tienda.id,
                precio_local="1000.00",
                tipo_cambio_usado="1250.0000",
                precio_usd="0.80",
            ),
            PrecioHistorico(
                timestamp=DIA2,
                producto_id=producto.id,
                tienda_id=tienda.id,
                precio_local="900.00",
                precio_tachado="1000.00",
                en_oferta=True,
                tipo_cambio_usado="1250.0000",
                precio_usd="0.72",
            ),
        ]
    )
    db_session.commit()
    return {"producto": producto, "tienda": tienda}


def test_history_devuelve_puntos_con_usd_y_promo(api_client, seed_precios) -> None:
    response = api_client.get(
        "/api/v1/prices/history",
        params={"producto_id": seed_precios["producto"].id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3

    primero, segundo, promo = body["items"]
    # DOD HU 3.3: mismo precio local, FX distinto => precio_usd distinto
    assert primero["precio_local"] == segundo["precio_local"] == "1000.00"
    assert primero["precio_usd"] == "1.00"
    assert segundo["precio_usd"] == "0.80"

    # DOD HU 2.2: clasificacion derivada en lectura
    assert primero["is_promotion"] is False
    assert primero["price_regular"] == "1000.00"
    assert promo["is_promotion"] is True
    assert promo["price_regular"] == "1000.00"
    assert promo["discount_pct"] == "0.1000"


def test_history_sin_filtros(api_client, seed_precios) -> None:
    response = api_client.get("/api/v1/prices/history")
    assert response.status_code == 200
    assert response.json()["total"] == 3


def test_history_filtra_por_tienda_y_rango(api_client, seed_precios) -> None:
    response = api_client.get(
        "/api/v1/prices/history",
        params={
            "tienda_id": seed_precios["tienda"].id,
            "start": "2026-11-02T00:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert all(
        item["timestamp"].startswith("2026-11-02")
        for item in body["items"]
    )


def test_history_producto_inexistente_devuelve_404(api_client) -> None:
    response = api_client.get(
        "/api/v1/prices/history",
        params={"producto_id": 99999},
    )
    assert response.status_code == 404


def test_history_paginacion_invalida_devuelve_422(api_client, seed_precios) -> None:
    response = api_client.get("/api/v1/prices/history", params={"page": 0})
    assert response.status_code == 422


def test_history_openapi_expone_los_campos(api_client) -> None:
    response = api_client.get("/openapi.json")
    schema = response.json()["components"]["schemas"]["PricePoint"]

    assert {
        "precio_local",
        "precio_usd",
        "tipo_cambio_usado",
        "en_oferta",
        "precio_tachado",
        "is_promotion",
        "price_regular",
        "discount_pct",
    } <= set(schema["properties"])
