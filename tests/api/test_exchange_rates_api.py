"""Integracion: GET /api/v1/exchange-rates (HU 3.2)."""

from datetime import UTC, datetime

import pytest

from src.models.historial_divisa import HistorialDivisa

T1 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
T2 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def seed_tasas(db_session) -> None:
    db_session.add_all(
        [
            HistorialDivisa(
                timestamp=T1,
                tipo_cambio_oficial="1000.0000",
                tipo_cambio_paralelo="1020.0000",
            ),
            HistorialDivisa(
                timestamp=T2,
                tipo_cambio_oficial="1010.0000",
                tipo_cambio_paralelo="1030.0000",
            ),
        ]
    )
    db_session.commit()


def test_history_devuelve_items_y_total(api_client, seed_tasas) -> None:
    response = api_client.get("/api/v1/exchange-rates/history")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["timestamp"].startswith("2026-11-01T09:00:00")
    assert body["items"][0]["tipo_cambio_oficial"] == "1000.0000"
    assert body["items"][1]["tipo_cambio_paralelo"] == "1030.0000"


def test_history_filtra_por_rango(api_client, seed_tasas) -> None:
    response = api_client.get(
        "/api/v1/exchange-rates/history",
        params={"start": "2026-11-01T10:00:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_as_of_timestamp_exacto(api_client, seed_tasas) -> None:
    response = api_client.get(
        "/api/v1/exchange-rates/as-of",
        params={"ts": "2026-11-01T12:00:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["tipo_cambio_oficial"] == "1010.0000"


def test_as_of_intermedio_toma_la_anterior(api_client, seed_tasas) -> None:
    response = api_client.get(
        "/api/v1/exchange-rates/as-of",
        params={"ts": "2026-11-01T13:00:00+00:00"},
    )

    assert response.status_code == 200
    assert response.json()["timestamp"].startswith("2026-11-01T12:00:00")


def test_as_of_antes_del_primer_registro_devuelve_el_mas_antiguo(
    api_client,
    seed_tasas,
) -> None:
    response = api_client.get(
        "/api/v1/exchange-rates/as-of",
        params={"ts": "2026-10-01T00:00:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["timestamp"].startswith("2026-11-01T09:00:00")


def test_as_of_sin_datos_devuelve_404(api_client) -> None:
    response = api_client.get(
        "/api/v1/exchange-rates/as-of",
        params={"ts": "2026-11-01T12:00:00Z"},
    )

    assert response.status_code == 404
    assert "cotizaciones" in response.json()["detail"]


def test_as_of_sin_ts_devuelve_422(api_client, seed_tasas) -> None:
    response = api_client.get("/api/v1/exchange-rates/as-of")
    assert response.status_code == 422
