"""Tests de unidad: deteccion de picos mediana movil + MAD (HU 3.4)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.analytics.spike_detection import detect_spikes

BASE = date(2026, 10, 1)


def _serie(valores: list[str]) -> list[tuple[date, Decimal]]:
    return [
        (BASE + timedelta(days=i), Decimal(v))
        for i, v in enumerate(valores)
    ]


def test_pico_sintetico_conocido_se_detecta() -> None:
    serie = _serie(["100", "101", "99", "100", "102", "150", "100"])

    picos = detect_spikes(serie, window=5, k=3)

    assert len(picos) == 1
    pico = picos[0]
    assert pico.date == BASE + timedelta(days=5)
    assert pico.value == Decimal(150)
    assert pico.score > Decimal(1)
    assert pico.mad > 0


def test_serie_suave_no_genera_picos() -> None:
    serie = _serie(["100", "101", "99", "100", "102", "101", "99"])

    assert detect_spikes(serie, window=5, k=3) == []


def test_mad_cero_detecta_desvio_exacto() -> None:
    serie = _serie(["100", "100", "100", "100", "100", "130", "100"])

    picos = detect_spikes(serie, window=5, k=3)

    assert len(picos) == 1
    assert picos[0].value == Decimal(130)
    assert picos[0].mad == Decimal(0)


def test_no_evalua_sin_ventana_completa() -> None:
    serie = _serie(["100", "200"])

    assert detect_spikes(serie, window=5, k=3) == []


def test_ignora_orden_de_entrada_y_ordena_por_fecha() -> None:
    desordenada = list(reversed(_serie(["100", "101", "99", "100", "102", "150", "100"])))

    picos = detect_spikes(desordenada, window=5, k=3)

    assert len(picos) == 1
    assert picos[0].date == BASE + timedelta(days=5)


def test_k_mas_estricto_no_detecta_pico_moderado() -> None:
    serie = _serie(["100", "101", "99", "100", "102", "110", "100"])

    assert len(detect_spikes(serie, window=5, k=3)) == 1
    assert detect_spikes(serie, window=5, k=10) == []


def test_parametros_invalidos() -> None:
    serie = _serie(["100", "101"])
    with pytest.raises(ValueError, match="window"):
        detect_spikes(serie, window=1)
    with pytest.raises(ValueError, match="k"):
        detect_spikes(serie, window=2, k=0)
