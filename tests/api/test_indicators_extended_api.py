"""Integracion: currency, devaluation-gap y spikes (HU 3.4)."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from src.models.historial_divisa import HistorialDivisa
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico

DIA1 = date(2026, 10, 1)
DIA7 = date(2026, 10, 7)


def _seed(db, valores: dict[date, tuple[str, str]]) -> ProductoCanonico:
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    db.add(producto)
    db.flush()
    for dia, (local, usd) in valores.items():
        db.add(
            PrecioHistorico(
                timestamp=datetime.combine(dia, time(10, 0), tzinfo=UTC),
                producto_id=producto.id,
                precio_local=local,
                tipo_cambio_usado="1000.0000",
                precio_usd=usd,
            )
        )
    db.add(
        HistorialDivisa(
            timestamp=datetime.combine(DIA1, time(0, 0), tzinfo=UTC),
            tipo_cambio_oficial="1000.0000",
            tipo_cambio_paralelo="1020.0000",
        )
    )
    db.add(
        HistorialDivisa(
            timestamp=datetime.combine(DIA7, time(12, 0), tzinfo=UTC),
            tipo_cambio_oficial="1200.0000",
            tipo_cambio_paralelo="1250.0000",
        )
    )
    db.commit()
    return producto


def test_inflation_currency_usd(api_client, db_session) -> None:
    _seed(db_session, {DIA1: ("1000.00", "1.00"), DIA7: ("1000.00", "0.80")})

    local = api_client.get(
        "/api/v1/indicators/inflation",
        params={"window_days": 1},
    ).json()
    usd = api_client.get(
        "/api/v1/indicators/inflation",
        params={"window_days": 1, "currency": "usd"},
    ).json()

    assert Decimal(local["series"][-1]["index"]) == Decimal("100.00")
    assert Decimal(usd["series"][-1]["index"]) == Decimal("80.00")


def test_inflation_currency_invalido_422(api_client) -> None:
    response = api_client.get(
        "/api/v1/indicators/inflation",
        params={"currency": "eur"},
    )
    assert response.status_code == 422


def test_devaluation_gap(api_client, db_session) -> None:
    _seed(db_session, {DIA1: ("100.00", "0.10"), DIA7: ("110.00", "0.11")})

    response = api_client.get(
        "/api/v1/indicators/devaluation-gap",
        params={
            "start_date": DIA1.isoformat(),
            "end_date": DIA7.isoformat(),
            "window_days": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["price_variation"]) == Decimal("0.1000")
    assert Decimal(body["fx_variation"]) == Decimal("0.2000")
    assert Decimal(body["gap"]) == Decimal("-0.1000")


def test_devaluation_gap_sin_precios_404(api_client, db_session) -> None:
    response = api_client.get(
        "/api/v1/indicators/devaluation-gap",
        params={"start_date": DIA1.isoformat(), "end_date": DIA7.isoformat()},
    )
    assert response.status_code == 404


def test_devaluation_gap_rango_invertido_400(api_client, db_session) -> None:
    _seed(db_session, {DIA1: ("100.00", "0.10"), DIA7: ("110.00", "0.11")})

    response = api_client.get(
        "/api/v1/indicators/devaluation-gap",
        params={
            "start_date": DIA7.isoformat(),
            "end_date": DIA1.isoformat(),
        },
    )
    assert response.status_code == 400


def test_devaluation_gap_fechas_invalidas_422(api_client) -> None:
    response = api_client.get(
        "/api/v1/indicators/devaluation-gap",
        params={"start_date": "mala", "end_date": DIA7.isoformat()},
    )
    assert response.status_code == 422


def test_spikes_detecta_pico(api_client, db_session) -> None:
    producto = _seed(
        db_session,
        {
            DIA1: ("100.00", "0.10"),
            date(2026, 10, 2): ("101.00", "0.10"),
            date(2026, 10, 3): ("99.00", "0.10"),
            date(2026, 10, 4): ("100.00", "0.10"),
            date(2026, 10, 5): ("102.00", "0.10"),
            date(2026, 10, 6): ("150.00", "0.15"),
            DIA7: ("100.00", "0.10"),
        },
    )

    response = api_client.get(
        "/api/v1/indicators/spikes",
        params={"producto_id": producto.id, "window": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["date"] == "2026-10-06"
    assert Decimal(item["value"]) == Decimal("150.00")


def test_spikes_producto_inexistente_404(api_client) -> None:
    response = api_client.get(
        "/api/v1/indicators/spikes",
        params={"producto_id": 9999},
    )
    assert response.status_code == 404


def test_spikes_parametros_invalidos_422(api_client, db_session) -> None:
    producto = _seed(db_session, {DIA1: ("100.00", "0.10")})

    assert (
        api_client.get(
            "/api/v1/indicators/spikes",
            params={"producto_id": producto.id, "window": 1},
        ).status_code
        == 422
    )
    assert (
        api_client.get(
            "/api/v1/indicators/spikes",
            params={"producto_id": producto.id, "k": 0},
        ).status_code
        == 422
    )
