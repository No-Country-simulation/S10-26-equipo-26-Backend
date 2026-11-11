"""Tests de unidad: indice de inflacion base sin promos (HU 2.3)."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from src.analytics.inflation import compute_inflation
from src.models.categoria import Categoria
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico


def _seed_producto(db, nombre: str, categoria_id: int | None) -> ProductoCanonico:
    producto = ProductoCanonico(
        nombre_universal=nombre,
        categoria_id=categoria_id,
    )
    db.add(producto)
    db.flush()
    return producto


def _seed_precio(
    db,
    producto_id: int,
    dia: date,
    precio: str,
    *,
    en_oferta: bool = False,
    precio_tachado: str | None = None,
) -> None:
    db.add(
        PrecioHistorico(
            timestamp=datetime.combine(dia, time(10, 0), tzinfo=UTC),
            producto_id=producto_id,
            precio_local=precio,
            precio_tachado=precio_tachado,
            en_oferta=en_oferta,
            tipo_cambio_usado="1000.0000",
            precio_usd="1.00",
        )
    )


def test_subida_real_con_promo_temporal_no_baja_el_indice(db_session) -> None:
    """DOD HU 2.3: subida real + promo temporal => el indice no baja."""
    producto = _seed_producto(db_session, "Coca Cola 2L", None)

    for i in range(1, 5):
        _seed_precio(db_session, producto.id, date(2026, 10, i), "100.00")
    _seed_precio(  # promo temporal (en_oferta)
        db_session,
        producto.id,
        date(2026, 10, 5),
        "80.00",
        en_oferta=True,
    )
    for i in range(6, 11):
        _seed_precio(db_session, producto.id, date(2026, 10, i), "110.00")
    db_session.commit()

    resultado = compute_inflation(db_session)

    assert resultado.excluded_promos == 1
    assert resultado.products_count == 1
    assert resultado.series[0].index == Decimal("100.00")
    assert min(p.index for p in resultado.series) >= Decimal("100.00")
    assert resultado.series[-1].index > Decimal("100.00")


def test_promo_no_entra_en_el_indice_con_ventana_unitaria(db_session) -> None:
    producto = _seed_producto(db_session, "Coca Cola 2L", None)

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

    resultado = compute_inflation(db_session, window_days=1)

    # si la promo entrara, habria un punto con index 80 en el dia 5
    assert all(p.index >= Decimal("100.00") for p in resultado.series)
    fechas = {p.date for p in resultado.series}
    # el dia 5 solo tiene precio en oferta: sin precio regular no hay punto
    assert date(2026, 10, 5) not in fechas
    assert date(2026, 10, 6) in fechas
    assert resultado.excluded_promos == 1


def test_descuento_sin_badge_tambien_excluido(db_session) -> None:
    producto = _seed_producto(db_session, "Yerba 1kg", None)
    _seed_precio(db_session, producto.id, date(2026, 10, 1), "100.00")
    _seed_precio(
        db_session,
        producto.id,
        date(2026, 10, 2),
        "85.00",
        precio_tachado="100.00",
    )
    db_session.commit()

    resultado = compute_inflation(db_session, window_days=1)

    assert resultado.excluded_promos == 1
    assert all(p.index == Decimal("100.00") for p in resultado.series)


def test_media_de_variaciones_por_producto(db_session) -> None:
    cat = Categoria(nombre="Tecnologia")
    db_session.add(cat)
    db_session.flush()

    sube = _seed_producto(db_session, "Auriculares", cat.id)
    plano = _seed_producto(db_session, "Mouse", cat.id)

    _seed_precio(db_session, sube.id, date(2026, 10, 1), "100.00")
    _seed_precio(db_session, sube.id, date(2026, 10, 8), "110.00")
    _seed_precio(db_session, plano.id, date(2026, 10, 1), "100.00")
    _seed_precio(db_session, plano.id, date(2026, 10, 8), "100.00")
    db_session.commit()

    resultado = compute_inflation(db_session, window_days=1)

    assert resultado.series[0].index == Decimal("100.00")
    # media de ratios: (1.10 + 1.00) / 2 => 105
    assert resultado.series[-1].index == Decimal("105.00")


def test_filtro_por_categoria(db_session) -> None:
    cat_a = Categoria(nombre="Alimentos")
    cat_b = Categoria(nombre="Moda")
    db_session.add_all([cat_a, cat_b])
    db_session.flush()

    dentro = _seed_producto(db_session, "Gaseosa", cat_a.id)
    fuera = _seed_producto(db_session, "Remera", cat_b.id)

    _seed_precio(db_session, dentro.id, date(2026, 10, 1), "100.00")
    _seed_precio(db_session, dentro.id, date(2026, 10, 8), "100.00")
    _seed_precio(db_session, fuera.id, date(2026, 10, 1), "100.00")
    _seed_precio(db_session, fuera.id, date(2026, 10, 8), "999.00")
    db_session.commit()

    resultado = compute_inflation(db_session, category_id=cat_a.id, window_days=1)

    assert resultado.products_count == 1
    assert resultado.series[-1].index == Decimal("100.00")


def test_rango_de_fechas(db_session) -> None:
    producto = _seed_producto(db_session, "Coca Cola 2L", None)
    for i in range(1, 11):
        _seed_precio(
            db_session,
            producto.id,
            date(2026, 10, i),
            "100.00",
        )
    db_session.commit()

    resultado = compute_inflation(
        db_session,
        start=date(2026, 10, 5),
        end=date(2026, 10, 7),
        window_days=1,
    )

    assert [p.date for p in resultado.series] == [
        date(2026, 10, 5),
        date(2026, 10, 6),
        date(2026, 10, 7),
    ]
    assert all(p.index == Decimal("100.00") for p in resultado.series)


def test_sin_datos_devuelve_serie_vacia(db_session) -> None:
    resultado = compute_inflation(db_session)

    assert resultado.series == []
    assert resultado.products_count == 0
    assert resultado.base == Decimal(100)
    assert resultado.excluded_promos == 0


def test_solo_promos_devuelve_serie_vacia(db_session) -> None:
    producto = _seed_producto(db_session, "Coca Cola 2L", None)
    _seed_precio(
        db_session,
        producto.id,
        date(2026, 10, 1),
        "80.00",
        en_oferta=True,
    )
    db_session.commit()

    resultado = compute_inflation(db_session)

    assert resultado.series == []
    assert resultado.excluded_promos == 1
