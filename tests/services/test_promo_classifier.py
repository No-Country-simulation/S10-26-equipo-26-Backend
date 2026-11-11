"""Tests de unidad: promo_classifier (HU 2.2) — bordes 0%, 9%, 10%."""

from decimal import Decimal

import pytest

from src.services.promo_classifier import classify


def test_descuento_0_por_ciento_no_es_promo() -> None:
    result = classify(precio="100.00", precio_tachado="100.00")
    assert result.is_promotion is False
    assert result.discount_pct == Decimal(0)
    assert result.price_regular == Decimal("100.00")


def test_descuento_9_por_ciento_no_es_promo() -> None:
    result = classify(precio="91.00", precio_tachado="100.00")
    assert result.discount_pct == Decimal("0.0900")
    assert result.is_promotion is False
    assert result.price_regular == Decimal("100.00")


def test_descuento_10_por_ciento_es_promo() -> None:
    result = classify(precio="90.00", precio_tachado="100.00")
    assert result.discount_pct == Decimal("0.1000")
    assert result.is_promotion is True
    assert result.price_regular == Decimal("100.00")


def test_descuento_grande_es_promo() -> None:
    result = classify(precio=50, precio_tachado=100)
    assert result.is_promotion is True
    assert result.discount_pct == Decimal("0.5000")


def test_sin_precio_tachado_no_es_promo() -> None:
    result = classify(precio="85.00")
    assert result.is_promotion is False
    assert result.discount_pct == Decimal(0)
    assert result.price_regular == Decimal("85.00")


def test_badge_en_oferta_sin_tachado_es_promo() -> None:
    result = classify(precio="85.00", en_oferta=True)
    assert result.is_promotion is True
    assert result.price_regular == Decimal("85.00")


def test_badge_en_oferta_con_descuento_chico_es_promo_por_badge() -> None:
    result = classify(precio="95.00", precio_tachado="100.00", en_oferta=True)
    assert result.is_promotion is True
    assert result.discount_pct == Decimal("0.0500")


def test_tachado_menor_o_igual_al_actual_no_descuenta() -> None:
    result = classify(precio="100.00", precio_tachado="90.00")
    assert result.is_promotion is False
    assert result.discount_pct == Decimal(0)
    assert result.price_regular == Decimal("100.00")


def test_umbral_configurable() -> None:
    result = classify(
        precio="93.00",
        precio_tachado="100.00",
        threshold="0.05",
    )
    assert result.discount_pct == Decimal("0.0700")
    assert result.is_promotion is True

    estricto = classify(
        precio="93.00",
        precio_tachado="100.00",
        threshold="0.10",
    )
    assert estricto.is_promotion is False


def test_precio_invalido_lanza_error() -> None:
    with pytest.raises(ValueError, match="precio"):
        classify(precio="0")
    with pytest.raises(ValueError, match="precio"):
        classify(precio="-5")


def test_threshold_invalido_lanza_error() -> None:
    with pytest.raises(ValueError, match="threshold"):
        classify(precio="100", threshold="-0.1")


def test_acepta_float_y_decimal() -> None:
    result = classify(precio=89.9, precio_tachado=Decimal(100))
    assert result.is_promotion is True
    assert result.price_regular == Decimal(100)
