"""Tests de unidad: store_product_service (HU 1.2)."""

import pytest

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models.categoria import Categoria
from src.models.producto_canonico import ProductoCanonico
from src.models.tienda import Tienda
from src.schemas.store_product import StoreProductCreate
from src.services import store_product_service


@pytest.fixture
def catalogo(db_session):
    categoria = Categoria(nombre="Alimentos y Bebidas")
    tienda = Tienda(nombre="Coto")
    otra_tienda = Tienda(nombre="Carrefour")
    producto = ProductoCanonico(nombre_universal="Coca Cola 2L")
    db_session.add_all([categoria, tienda, otra_tienda, producto])
    db_session.commit()
    return {"tienda": tienda, "otra": otra_tienda, "producto": producto}


def test_create_vinculado(db_session, catalogo) -> None:
    creado = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            producto_id=catalogo["producto"].id,
            tienda_id=catalogo["tienda"].id,
            external_id="EXT-1",
            nombre_crudo="COCA COLA 2 LT",
            source_url="https://www.coto.com.ar/p/1",
        ),
    )

    assert creado.id is not None
    assert creado.producto_id == catalogo["producto"].id
    assert creado.created_at is not None


def test_create_sin_producto_id_permitido(db_session, catalogo) -> None:
    """Scraping antes del match: producto_id NULL (HU 1.4 asiste)."""
    creado = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            tienda_id=catalogo["tienda"].id,
            external_id="EXT-NUEVO",
            nombre_crudo="COCA COLA 2 LITROS",
        ),
    )

    assert creado.producto_id is None

    pendientes = store_product_service.list_store_products(
        db_session,
        unmatched_only=True,
    )
    assert [s.id for s in pendientes] == [creado.id]


def test_create_duplicado_lanza_conflict(db_session, catalogo) -> None:
    payload = StoreProductCreate(
        producto_id=catalogo["producto"].id,
        tienda_id=catalogo["tienda"].id,
        external_id="EXT-1",
        nombre_crudo="COCA COLA 2 LT",
    )
    store_product_service.create_store_product(db_session, payload)

    with pytest.raises(ConflictError, match="ya vinculado"):
        store_product_service.create_store_product(db_session, payload)

    db_session.rollback()


def test_mismo_external_id_en_otra_tienda_no_conflicta(
    db_session,
    catalogo,
) -> None:
    store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            tienda_id=catalogo["tienda"].id,
            external_id="EXT-1",
            nombre_crudo="COCA COLA 2 LT",
        ),
    )
    otro = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            tienda_id=catalogo["otra"].id,
            external_id="EXT-1",
            nombre_crudo="Coca-Cola 2 litros",
        ),
    )

    assert otro.id is not None


def test_create_producto_inexistente_rechazado(db_session, catalogo) -> None:
    with pytest.raises(ValidationError, match="producto_id"):
        store_product_service.create_store_product(
            db_session,
            StoreProductCreate(
                producto_id=9999,
                tienda_id=catalogo["tienda"].id,
                external_id="EXT-2",
                nombre_crudo="X",
            ),
        )


def test_create_tienda_inexistente_rechazada(db_session, catalogo) -> None:
    with pytest.raises(ValidationError, match="tienda_id"):
        store_product_service.create_store_product(
            db_session,
            StoreProductCreate(
                tienda_id=9999,
                external_id="EXT-3",
                nombre_crudo="X",
            ),
        )


def test_get_y_404(db_session, catalogo) -> None:
    creado = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            tienda_id=catalogo["tienda"].id,
            external_id="EXT-9",
            nombre_crudo="X",
        ),
    )

    assert store_product_service.get_store_product(db_session, creado.id).id == creado.id

    with pytest.raises(NotFoundError, match="no encontrado"):
        store_product_service.get_store_product(db_session, 99999)


def test_list_filtros(db_session, catalogo) -> None:
    vinculado = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            producto_id=catalogo["producto"].id,
            tienda_id=catalogo["tienda"].id,
            external_id="EXT-A",
            nombre_crudo="A",
        ),
    )
    sin_match = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            tienda_id=catalogo["tienda"].id,
            external_id="EXT-B",
            nombre_crudo="B",
        ),
    )
    en_otra_tienda = store_product_service.create_store_product(
        db_session,
        StoreProductCreate(
            tienda_id=catalogo["otra"].id,
            external_id="EXT-C",
            nombre_crudo="C",
        ),
    )

    por_tienda = store_product_service.list_store_products(
        db_session,
        tienda_id=catalogo["tienda"].id,
    )
    assert len(por_tienda) == 2

    por_producto = store_product_service.list_store_products(
        db_session,
        producto_id=catalogo["producto"].id,
    )
    assert [s.id for s in por_producto] == [vinculado.id]

    pendientes = store_product_service.list_store_products(
        db_session,
        unmatched_only=True,
    )
    assert [s.id for s in pendientes] == [sin_match.id, en_otra_tienda.id]
