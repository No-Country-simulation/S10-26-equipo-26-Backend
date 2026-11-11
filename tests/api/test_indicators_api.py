"""Integracion: GET /api/v1/indicators/inflation (HU 2.3)."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from src.models.categoria import Categoria
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico


def _seed_precio(db, producto_id: int, dia: date, precio: str, **kwargs) -> None:
    db.add(
        PrecioHistorico(
            timestamp=datetime.combine(dia, time(10, 0), tzinfo=UTC),
            producto_id=producto_id,
            precio_local=precio,
            tipo_cambio_usado="1000.0000",
            precio_usd="1.00",
            **kwargs,
        )
    )


@pytest.fixture
def seed_inflacion(db_session):
    cat = Categoria(nombre="Alimentos y Bebidas")
    db_session.add(cat)
    db_session.flush()

    producto = ProductoCanonico(
        nombre_universal="Coca Cola 2L",
        categoria_id=cat.id,
    )
    db_session.add(producto)
    db_session.flush()

    for i in range(1, 5):
        _seed_precio(db_session, producto.id, date(2026, 10, i), "100.00")
    _seed_precio(
        db_session,
        producto.id,
        date(2026, 10, 5),
        "80.00",
        en_oferta=True,
    )
    for i in range(6, 11):
        _seed_precio(db_session, producto.id, date(2026, 10, i), "110.00")
    db_session.commit()
    return {"producto": producto, "categoria": cat}


def test_inflation_devuelve_serie_base_100_sin_bajar(
    api_client,
    seed_inflacion,
) -> None:
    response = api_client.get("/api/v1/indicators/inflation")

    assert response.status_code == 200
    body = response.json()

    assert body["base"] == "100"
    assert body["excluded_promos"] == 1
    assert body["products_count"] == 1
    assert body["method"]

    indices = [Decimal(p["index"]) for p in body["series"]]
    assert indices[0] == Decimal("100.00")
    assert min(indices) >= Decimal("100.00")
    assert indices[-1] > Decimal("100.00")


def test_inflation_filtra_por_categoria(api_client, seed_inflacion) -> None:
    response = api_client.get(
        "/api/v1/indicators/inflation",
        params={"category_id": seed_inflacion["categoria"].id},
    )

    assert response.status_code == 200
    assert response.json()["products_count"] == 1

    vacio = api_client.get(
        "/api/v1/indicators/inflation",
        params={"category_id": 9999},
    )
    assert vacio.status_code == 200
    assert vacio.json()["series"] == []


def test_inflation_rango_de_fechas(api_client, seed_inflacion) -> None:
    response = api_client.get(
        "/api/v1/indicators/inflation",
        params={"start_date": "2026-10-06", "end_date": "2026-10-08"},
        # window mira hacia atras; sin datos previos en el rango el base
        # es la primera fecha con datos
    )

    assert response.status_code == 200
    fechas = [p["date"] for p in response.json()["series"]]
    assert fechas
    assert all("2026-10-06" <= f <= "2026-10-08" for f in fechas)


def test_inflation_sin_datos(api_client) -> None:
    response = api_client.get("/api/v1/indicators/inflation")

    assert response.status_code == 200
    body = response.json()
    assert body["series"] == []
    assert body["products_count"] == 0


def test_inflation_params_invalidos_devuelven_422(api_client) -> None:
    assert (
        api_client.get(
            "/api/v1/indicators/inflation",
            params={"window_days": 0},
        ).status_code
        == 422
    )
    assert (
        api_client.get(
            "/api/v1/indicators/inflation",
            params={"start_date": "no-es-fecha"},
        ).status_code
        == 422
    )
    assert (
        api_client.get(
            "/api/v1/indicators/inflation",
            params={"category_id": "abc"},
        ).status_code
        == 422
    )


def test_inflation_documentado_en_openapi(api_client) -> None:
    schema = api_client.get("/openapi.json").json()
    ruta = schema["paths"]["/api/v1/indicators/inflation"]["get"]

    params = {p["name"] for p in ruta["parameters"]}
    assert {"category_id", "start_date", "end_date"} <= params
    assert "InflationSeriesRead" in str(ruta["responses"]["200"])
