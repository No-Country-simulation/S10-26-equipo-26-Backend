"""Tests de unidad: fx_service.get_rate_as_of (HU 3.2).

Constantes NAIVE: SQLite devuelve datetimes sin tz (en Railway/PG se
devuelven aware; los schemas normalizan a UTC en la capa API).
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from src.core.exceptions import NotFoundError
from src.models.historial_divisa import HistorialDivisa
from src.services import fx_service

T1 = datetime(2026, 11, 1, 9, 0)
T2 = datetime(2026, 11, 1, 12, 0)
T3 = datetime(2026, 11, 1, 15, 0)


@pytest.fixture
def tasas(db_session) -> list[HistorialDivisa]:
    filas = [
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
        HistorialDivisa(
            timestamp=T3,
            tipo_cambio_oficial="1020.0000",
            tipo_cambio_paralelo="1040.0000",
        ),
    ]
    db_session.add_all(filas)
    db_session.commit()
    return filas


def test_as_of_timestamp_exacto(db_session, tasas) -> None:
    resultado = fx_service.get_rate_as_of(db_session, T2)
    assert resultado.timestamp == T2
    assert resultado.tipo_cambio_oficial == 1010


def test_as_of_timestamp_intermedio(db_session, tasas) -> None:
    resultado = fx_service.get_rate_as_of(
        db_session,
        datetime(2026, 11, 1, 13, 30, tzinfo=UTC),
    )
    assert resultado.timestamp == T2


def test_as_of_anterior_al_primer_registro_usa_el_mas_antiguo(
    db_session,
    tasas,
) -> None:
    resultado = fx_service.get_rate_as_of(
        db_session,
        datetime(2026, 10, 31, 23, 0, tzinfo=UTC),
    )
    assert resultado.timestamp == T1


def test_as_of_sin_registros_lanza_404(db_session) -> None:
    with pytest.raises(NotFoundError, match="no hay cotizaciones"):
        fx_service.get_rate_as_of(db_session, T2)


def test_as_of_con_timestamp_naive_se_trata_como_utc(
    db_session,
    tasas,
) -> None:
    resultado = fx_service.get_rate_as_of(
        db_session,
        datetime(2026, 11, 1, 13, 30),
    )
    assert resultado.timestamp == T2


def test_history_rango_y_orden(db_session, tasas) -> None:
    todo = fx_service.get_history(db_session)
    assert [f.timestamp for f in todo] == [T1, T2, T3]

    rango = fx_service.get_history(
        db_session,
        start=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
        end=datetime(2026, 11, 1, 14, 0, tzinfo=UTC),
    )
    assert [f.timestamp for f in rango] == [T2]

    limitado = fx_service.get_history(db_session, limit=2)
    assert len(limitado) == 2


def test_history_vacio_devuelve_lista(db_session) -> None:
    assert fx_service.get_history(db_session) == []


def test_as_of_aware_diferente_offset_equivalente(db_session, tasas) -> None:
    # 09:00 con offset -03:00 equivale a 12:00 UTC => T2
    otra_zona = datetime(
        2026,
        11,
        1,
        9,
        0,
        tzinfo=timezone(timedelta(hours=-3)),
    )
    resultado = fx_service.get_rate_as_of(db_session, otra_zona)
    assert resultado.timestamp == T2
