"""Tests de unidad: product_service (HU 1.1)."""

import pytest

from src.core.exceptions import NotFoundError, ValidationError
from src.models.categoria import Categoria
from src.schemas.producto_canonico import (
    ProductoCanonicoCreate,
    ProductoCanonicoUpdate,
)
from src.services import product_service


@pytest.fixture
def categoria(db_session) -> Categoria:
    categoria = Categoria(nombre="Alimentos y Bebidas")
    db_session.add(categoria)
    db_session.commit()
    return categoria


def test_create_y_get_producto(db_session, categoria) -> None:
    creado = product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Coca Cola 2L",
            categoria_id=categoria.id,
            marca="Coca Cola",
            unidad_medida="2 L",
        ),
    )

    assert creado.id is not None
    assert creado.nombre_universal == "Coca Cola 2L"
    assert creado.categoria_id == categoria.id

    obtenido = product_service.get_product(db_session, creado.id)
    assert obtenido.id == creado.id


def test_create_con_categoria_inexistente_rechazado(db_session) -> None:
    with pytest.raises(ValidationError, match="no existe"):
        product_service.create_product(
            db_session,
            ProductoCanonicoCreate(
                nombre_universal="Producto huerfano",
                categoria_id=999,
            ),
        )


def test_create_sin_categoria_valida(db_session) -> None:
    creado = product_service.create_product(
        db_session,
        ProductoCanonicoCreate(nombre_universal="Sin categoria"),
    )
    assert creado.categoria_id is None


def test_get_producto_inexistente_lanza_404(db_session) -> None:
    with pytest.raises(NotFoundError, match="no encontrado"):
        product_service.get_product(db_session, 12345)


def test_list_filtra_por_categoria(db_session, categoria) -> None:
    otra = Categoria(nombre="Tecnologia")
    db_session.add(otra)
    db_session.flush()

    product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Coca Cola 2L",
            categoria_id=categoria.id,
        ),
    )
    product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Auriculares X",
            categoria_id=otra.id,
        ),
    )

    resultado = product_service.list_products(
        db_session,
        category_id=categoria.id,
    )
    assert resultado.total == 1
    assert resultado.items[0].nombre_universal == "Coca Cola 2L"


def test_list_busca_por_nombre_y_marca(db_session, categoria) -> None:
    product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Coca Cola 2L",
            marca="Coca Cola",
            categoria_id=categoria.id,
        ),
    )
    product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Auriculares Bluetooth",
            marca="Sony",
            categoria_id=categoria.id,
        ),
    )

    por_nombre = product_service.list_products(db_session, search="coca")
    assert por_nombre.total == 1
    assert por_nombre.items[0].marca == "Coca Cola"

    por_marca = product_service.list_products(db_session, search="SONY")
    assert por_marca.total == 1

    vacio = product_service.list_products(db_session, search="inexistente")
    assert vacio.total == 0
    assert vacio.items == []


def test_list_paginacion(db_session, categoria) -> None:
    for i in range(3):
        product_service.create_product(
            db_session,
            ProductoCanonicoCreate(
                nombre_universal=f"Producto {i:02d}",
                categoria_id=categoria.id,
            ),
        )

    pagina1 = product_service.list_products(db_session, page=1, page_size=2)
    pagina2 = product_service.list_products(db_session, page=2, page_size=2)

    assert pagina1.total == 3
    assert len(pagina1.items) == 2
    assert len(pagina2.items) == 1
    assert pagina1.items[0].nombre_universal == "Producto 00"


def test_update_producto(db_session, categoria) -> None:
    producto = product_service.create_product(
        db_session,
        ProductoCanonicoCreate(nombre_universal="Nombre viejo"),
    )
    nueva_categoria = Categoria(nombre="Hogar y Limpieza")
    db_session.add(nueva_categoria)
    db_session.commit()

    actualizado = product_service.update_product(
        db_session,
        producto.id,
        ProductoCanonicoUpdate(
            nombre_universal="Nombre nuevo",
            categoria_id=nueva_categoria.id,
        ),
    )

    assert actualizado.nombre_universal == "Nombre nuevo"
    assert actualizado.categoria_id == nueva_categoria.id

    parcial = product_service.update_product(
        db_session,
        producto.id,
        ProductoCanonicoUpdate(marca="Solo Marca"),
    )
    assert parcial.nombre_universal == "Nombre nuevo"
    assert parcial.marca == "Solo Marca"


def test_update_con_categoria_inexistente_rechazado(db_session) -> None:
    producto = product_service.create_product(
        db_session,
        ProductoCanonicoCreate(nombre_universal="Producto X"),
    )
    with pytest.raises(ValidationError, match="no existe"):
        product_service.update_product(
            db_session,
            producto.id,
            ProductoCanonicoUpdate(categoria_id=999),
        )


def test_update_producto_inexistente_lanza_404(db_session) -> None:
    with pytest.raises(NotFoundError):
        product_service.update_product(
            db_session,
            999,
            ProductoCanonicoUpdate(nombre_universal="Nada"),
        )


def test_list_categories(db_session) -> None:
    db_session.add_all(
        [
            Categoria(nombre="Tecnologia"),
            Categoria(nombre="Alimentos y Bebidas"),
        ]
    )
    db_session.commit()

    categorias = product_service.list_categories(db_session)
    assert [c.nombre for c in categorias] == [
        "Alimentos y Bebidas",
        "Tecnologia",
    ]
