"""Integracion: POST /api/v1/match/suggestions (HU 1.4)."""

import pytest

from src.models.producto_canonico import ProductoCanonico
from src.models.store_product import StoreProduct
from src.models.tienda import Tienda


@pytest.fixture
def seed_matching(db_session):
    tienda = Tienda(nombre="Coto")
    producto_coca = ProductoCanonico(nombre_universal="Coca Cola 500 ml")
    producto_coca_2l = ProductoCanonico(nombre_universal="Coca Cola 2 L")
    producto_agua = ProductoCanonico(nombre_universal="Agua Villavicencio 2 l")
    db_session.add_all([tienda, producto_coca, producto_coca_2l, producto_agua])
    db_session.flush()

    db_session.add_all(
        [
            StoreProduct(
                tienda_id=tienda.id,
                external_id="EXT-1",
                nombre_crudo="COCA-COLA 500 ml",
            ),
            StoreProduct(
                tienda_id=tienda.id,
                external_id="EXT-2",
                nombre_crudo="Coca Cola 2 litros",
            ),
            StoreProduct(
                tienda_id=tienda.id,
                external_id="EXT-3",
                nombre_crudo="Agua Villavicencio 2 l",
            ),
        ]
    )
    db_session.commit()
    return {"tienda": tienda}


def test_suggestions_devuelve_pares_con_score(api_client, seed_matching) -> None:
    response = api_client.post(
        "/api/v1/match/suggestions",
        json={"tienda_id": seed_matching["tienda"].id},
    )

    assert response.status_code == 200
    body = response.json()

    # EXT-1 auto vs coca; EXT-2 review (0.84) vs coca; EXT-3 auto vs agua
    assert body["total"] == 3
    assert body["auto_count"] == 2
    assert body["review_count"] == 1

    item = next(
        i for i in body["items"] if i["store_product"]["external_id"] == "EXT-1"
    )
    assert item["product"]["nombre_universal"] == "Coca Cola 500 ml"
    assert item["score"] >= 0.90
    assert item["band"] == "auto"


def test_suggestions_threshold_alto_filtra_review(api_client, seed_matching) -> None:
    response = api_client.post(
        "/api/v1/match/suggestions",
        json={"tienda_id": seed_matching["tienda"].id, "threshold": 0.85},
    )

    assert response.status_code == 200
    # EXT-2 (0.8387) queda bajo el umbral 0.85
    assert response.json()["total"] == 2
    assert response.json()["review_count"] == 0


def test_suggestions_tienda_inexistente_404(api_client) -> None:
    response = api_client.post(
        "/api/v1/match/suggestions",
        json={"tienda_id": 9999},
    )
    assert response.status_code == 404


def test_suggestions_payload_invalido_422(api_client) -> None:
    assert (
        api_client.post(
            "/api/v1/match/suggestions",
            json={"tienda_id": 0},
        ).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/v1/match/suggestions",
            json={"tienda_id": 1, "threshold": 1.5},
        ).status_code
        == 422
    )
    assert (
        api_client.post("/api/v1/match/suggestions", json={}).status_code
        == 422
    )
