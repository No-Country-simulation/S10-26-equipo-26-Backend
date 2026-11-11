"""Integracion: /api/v1/alerts (HU 3.5)."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from src.models.historial_divisa import HistorialDivisa
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico

DIA1 = date(2026, 10, 1)
DIA7 = date(2026, 10, 7)


@pytest.fixture
def seed_alertas(db_session) -> ProductoCanonico:
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    db_session.add(producto)
    db_session.flush()

    for dia, precio in ((DIA1, "100.00"), (DIA7, "130.00")):
        db_session.add(
            PrecioHistorico(
                timestamp=datetime.combine(dia, time(10, 0), tzinfo=UTC),
                producto_id=producto.id,
                precio_local=precio,
                tipo_cambio_usado="1000.0000",
                precio_usd=Decimal(precio) / Decimal(1000),
            )
        )
    db_session.add_all(
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
    db_session.commit()
    return producto


def test_evaluate_crea_alerta(api_client, seed_alertas) -> None:
    response = api_client.post(
        "/api/v1/alerts/evaluate",
        params={
            "start_date": DIA1.isoformat(),
            "end_date": DIA7.isoformat(),
            "window_days": 1,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    alerta = body[0]
    assert alerta["alert_type"] == "outpace_devaluation"
    assert alerta["severity"] == "medium"
    assert alerta["status"] == "open"
    assert Decimal(alerta["score"]) == Decimal("0.1000")

    # idempotente
    segunda = api_client.post(
        "/api/v1/alerts/evaluate",
        params={
            "start_date": DIA1.isoformat(),
            "end_date": DIA7.isoformat(),
            "window_days": 1,
        },
    )
    assert segunda.status_code == 201
    assert segunda.json() == []


def test_list_y_filtros(api_client, seed_alertas) -> None:
    creada = api_client.post(
        "/api/v1/alerts/evaluate",
        params={
            "start_date": DIA1.isoformat(),
            "end_date": DIA7.isoformat(),
            "window_days": 1,
        },
    ).json()[0]

    todos = api_client.get("/api/v1/alerts")
    assert todos.status_code == 200
    assert len(todos.json()) == 1

    por_status = api_client.get("/api/v1/alerts", params={"status": "open"})
    assert len(por_status.json()) == 1

    por_tipo = api_client.get(
        "/api/v1/alerts",
        params={"type": "shrinkflation"},
    )
    assert por_tipo.json() == []

    por_severidad = api_client.get(
        "/api/v1/alerts",
        params={"severity": "medium"},
    )
    assert len(por_severidad.json()) == 1
    assert por_severidad.json()[0]["id"] == creada["id"]


def test_patch_marca_como_revisada(api_client, seed_alertas) -> None:
    creada = api_client.post(
        "/api/v1/alerts/evaluate",
        params={
            "start_date": DIA1.isoformat(),
            "end_date": DIA7.isoformat(),
            "window_days": 1,
        },
    ).json()[0]

    response = api_client.patch(
        f"/api/v1/alerts/{creada['id']}",
        json={"status": "reviewed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewed"
    assert body["reviewed_at"] is not None

    abiertas = api_client.get("/api/v1/alerts", params={"status": "open"})
    assert abiertas.json() == []
    revisadas = api_client.get(
        "/api/v1/alerts",
        params={"status": "reviewed"},
    )
    assert len(revisadas.json()) == 1


def test_patch_alerta_inexistente_404(api_client) -> None:
    response = api_client.patch(
        "/api/v1/alerts/99999",
        json={"status": "reviewed"},
    )
    assert response.status_code == 404


def test_patch_status_invalido_422(api_client) -> None:
    response = api_client.patch(
        "/api/v1/alerts/1",
        json={"status": "borrada"},
    )
    assert response.status_code == 422


def test_evaluate_rango_invertido_400(api_client) -> None:
    response = api_client.post(
        "/api/v1/alerts/evaluate",
        params={
            "start_date": DIA7.isoformat(),
            "end_date": DIA1.isoformat(),
        },
    )
    assert response.status_code == 400


def test_evaluate_sin_cotizaciones_404(api_client, db_session) -> None:
    producto = ProductoCanonico(nombre_universal="Sin FX")
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

    response = api_client.post(
        "/api/v1/alerts/evaluate",
        params={"start_date": DIA1.isoformat(), "end_date": DIA7.isoformat()},
    )
    assert response.status_code == 404
