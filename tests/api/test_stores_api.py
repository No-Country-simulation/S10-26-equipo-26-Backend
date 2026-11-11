"""Integracion: GET /api/v1/stores."""

from src.models.tienda import Tienda


def test_list_stores(api_client, db_session) -> None:
    db_session.add_all(
        [
            Tienda(nombre="Coto", url_base="https://www.coto.com.ar/"),
            Tienda(nombre="Carrefour", url_base="https://www.carrefour.com.ar/"),
        ]
    )
    db_session.commit()

    response = api_client.get("/api/v1/stores")

    assert response.status_code == 200
    body = response.json()
    assert [t["nombre"] for t in body] == ["Coto", "Carrefour"]  # orden por id
    assert body[0]["url_base"] == "https://www.coto.com.ar/"
    assert all(isinstance(t["id"], int) for t in body)


def test_list_stores_vacio(api_client) -> None:
    response = api_client.get("/api/v1/stores")
    assert response.status_code == 200
    assert response.json() == []
