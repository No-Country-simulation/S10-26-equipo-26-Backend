"""Integracion: POST/GET /api/v1/store-products (HU 1.2)."""

import pytest

from src.models.tienda import Tienda


@pytest.fixture
def tienda(db_session) -> Tienda:
    tienda = Tienda(nombre="Coto")
    db_session.add(tienda)
    db_session.commit()
    return tienda


def test_post_devuelve_201(api_client, tienda) -> None:
    response = api_client.post(
        "/api/v1/store-products",
        json={
            "tienda_id": tienda.id,
            "external_id": "EXT-1",
            "nombre_crudo": "COCA COLA 2 LT",
            "source_url": "https://www.coto.com.ar/p/1",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["producto_id"] is None
    assert body["nombre_crudo"] == "COCA COLA 2 LT"
    assert body["created_at"]


def test_post_duplicado_devuelve_409(api_client, tienda) -> None:
    payload = {
        "tienda_id": tienda.id,
        "external_id": "EXT-1",
        "nombre_crudo": "COCA COLA 2 LT",
    }
    primero = api_client.post("/api/v1/store-products", json=payload)
    assert primero.status_code == 201

    duplicado = api_client.post(
        "/api/v1/store-products",
        json={**payload, "nombre_crudo": "otro nombre"},
    )

    assert duplicado.status_code == 409
    assert "ya vinculado" in duplicado.json()["detail"]


def test_post_tienda_inexistente_devuelve_400(api_client) -> None:
    response = api_client.post(
        "/api/v1/store-products",
        json={"tienda_id": 9999, "external_id": "E", "nombre_crudo": "X"},
    )
    assert response.status_code == 400


def test_post_producto_inexistente_devuelve_400(api_client, tienda) -> None:
    response = api_client.post(
        "/api/v1/store-products",
        json={
            "producto_id": 9999,
            "tienda_id": tienda.id,
            "external_id": "E",
            "nombre_crudo": "X",
        },
    )
    assert response.status_code == 400


def test_post_payload_invalido_devuelve_422(api_client, tienda) -> None:
    response = api_client.post(
        "/api/v1/store-products",
        json={"tienda_id": tienda.id, "external_id": "", "nombre_crudo": "X"},
    )
    assert response.status_code == 422


def test_get_list_filtros(api_client, tienda, db_session) -> None:
    otra = Tienda(nombre="Carrefour")
    db_session.add(otra)
    db_session.commit()

    api_client.post(
        "/api/v1/store-products",
        json={
            "tienda_id": tienda.id,
            "external_id": "EXT-A",
            "nombre_crudo": "A",
        },
    )
    api_client.post(
        "/api/v1/store-products",
        json={
            "tienda_id": tienda.id,
            "external_id": "EXT-B",
            "nombre_crudo": "B",
            "producto_id": None,
        },
    )
    api_client.post(
        "/api/v1/store-products",
        json={
            "tienda_id": otra.id,
            "external_id": "EXT-C",
            "nombre_crudo": "C",
        },
    )

    todos = api_client.get("/api/v1/store-products")
    assert todos.status_code == 200
    assert len(todos.json()) == 3

    por_tienda = api_client.get(
        "/api/v1/store-products",
        params={"tienda_id": tienda.id},
    )
    assert len(por_tienda.json()) == 2

    pendientes = api_client.get(
        "/api/v1/store-products",
        params={"unmatched_only": True},
    )
    assert len(pendientes.json()) == 3  # ninguno tiene producto_id


def test_get_por_id(api_client, tienda) -> None:
    creado = api_client.post(
        "/api/v1/store-products",
        json={
            "tienda_id": tienda.id,
            "external_id": "EXT-1",
            "nombre_crudo": "X",
        },
    ).json()

    ok = api_client.get(f"/api/v1/store-products/{creado['id']}")
    assert ok.status_code == 200
    assert ok.json()["id"] == creado["id"]

    no_existe = api_client.get("/api/v1/store-products/99999")
    assert no_existe.status_code == 404
