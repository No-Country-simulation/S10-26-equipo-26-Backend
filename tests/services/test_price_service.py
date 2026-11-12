"""Tests de unidad: price_service (HU 3.3) + clasificacion promo al leer."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.core.exceptions import NotFoundError
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.models.tienda import Tienda
from src.services import price_service

DIA1 = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
DIA2 = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)


@pytest.fixture
def escenario(db_session):
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    tienda = Tienda(nombre="Coto")
    db_session.add_all([producto, tienda])
    db_session.flush()

    filas = [
        PrecioHistorico(
            timestamp=DIA1,
            producto_id=producto.id,
            tienda_id=tienda.id,
            precio_local="1000.00",
            tipo_cambio_usado="1000.0000",
            precio_usd="1.00",
        ),
        PrecioHistorico(
            timestamp=DIA2,
            producto_id=producto.id,
            tienda_id=tienda.id,
            precio_local="1000.00",
            tipo_cambio_usado="1250.0000",
            precio_usd="0.80",
        ),
        PrecioHistorico(
            timestamp=DIA2 + timedelta(hours=1),
            producto_id=producto.id,
            tienda_id=tienda.id,
            precio_local="900.00",
            precio_tachado="1000.00",
            en_oferta=True,
            tipo_cambio_usado="1250.0000",
            precio_usd="0.72",
        ),
    ]
    db_session.add_all(filas)
    db_session.commit()
    return {"producto": producto, "tienda": tienda, "filas": filas}


def test_history_devuelve_precio_usd_persistido(escenario, db_session) -> None:
    resultado = price_service.get_price_history(
        db_session,
        producto_id=escenario["producto"].id,
    )

    assert resultado.total == 3
    mismo_precio_local = resultado.items[:2]
    assert mismo_precio_local[0].precio_local == mismo_precio_local[1].precio_local
    assert mismo_precio_local[0].precio_usd != mismo_precio_local[1].precio_usd
    assert mismo_precio_local[0].tipo_cambio_usado == Decimal("1000.0000")
    assert mismo_precio_local[1].tipo_cambio_usado == Decimal("1250.0000")


def test_history_clasifica_promo_al_leer(escenario, db_session) -> None:
    resultado = price_service.get_price_history(
        db_session,
        producto_id=escenario["producto"].id,
    )

    regular_1, _regular_2, promo = resultado.items
    assert regular_1.is_promotion is False
    assert regular_1.price_regular == Decimal("1000.00")
    assert regular_1.discount_pct == Decimal(0)

    assert promo.is_promotion is True
    assert promo.price_regular == Decimal("1000.00")
    assert promo.discount_pct == Decimal("0.1000")


def test_history_filtra_por_tienda(db_session, escenario) -> None:
    otra = Tienda(nombre="Carrefour")
    db_session.add(otra)
    db_session.flush()
    db_session.add(
        PrecioHistorico(
            timestamp=DIA1,
            producto_id=escenario["producto"].id,
            tienda_id=otra.id,
            precio_local="950.00",
            tipo_cambio_usado="1000.0000",
            precio_usd="0.95",
        )
    )
    db_session.commit()

    coto = price_service.get_price_history(
        db_session,
        tienda_id=escenario["tienda"].id,
    )
    assert coto.total == 3

    carrefour = price_service.get_price_history(db_session, tienda_id=otra.id)
    assert carrefour.total == 1
    assert carrefour.items[0].tienda_id == otra.id


def test_history_filtra_por_rango_temporal(db_session, escenario) -> None:
    resultado = price_service.get_price_history(
        db_session,
        producto_id=escenario["producto"].id,
        start=DIA2,
    )
    assert resultado.total == 2
    assert all(item.timestamp >= DIA2 for item in resultado.items)


def test_history_producto_inexistente_lanza_404(db_session) -> None:
    with pytest.raises(NotFoundError, match="no encontrado"):
        price_service.get_price_history(db_session, producto_id=99999)


def test_history_paginacion(db_session, escenario) -> None:
    pagina1 = price_service.get_price_history(
        db_session,
        producto_id=escenario["producto"].id,
        page=1,
        page_size=2,
    )
    assert pagina1.total == 3
    assert len(pagina1.items) == 2

    pagina2 = price_service.get_price_history(
        db_session,
        producto_id=escenario["producto"].id,
        page=2,
        page_size=2,
    )
    assert len(pagina2.items) == 1


def test_history_vacio(db_session) -> None:
    resultado = price_service.get_price_history(db_session)
    assert resultado.total == 0
    assert resultado.items == []

def test_history_incluye_raw_presentation(db_session) -> None:
    producto = ProductoCanonico(nombre_universal="Yerba 500 g")
    tienda = Tienda(nombre="Coto")
    db_session.add_all([producto, tienda])
    db_session.flush()
    db_session.add(
        PrecioHistorico(
            timestamp=DIA1,
            producto_id=producto.id,
            tienda_id=tienda.id,
            precio_local="1000.00",
            tipo_cambio_usado="1000.0000",
            precio_usd="1.00",
            raw_presentation="Yerba 500 g",
        )
    )
    db_session.commit()

    resultado = price_service.get_price_history(db_session, producto_id=producto.id)

    assert resultado.items[0].raw_presentation == "Yerba 500 g"
