"""Integracion: endpoints /api/v1/products y /api/v1/products/categories (HU 1.1)."""


def test_post_products_devuelve_201(api_client, db_session) -> None:
    from src.models.categoria import Categoria

    categoria = Categoria(nombre="Tecnologia")
    db_session.add(categoria)
    db_session.commit()

    response = api_client.post(
        "/api/v1/products",
        json={
            "nombre_universal": "Auriculares Sony",
            "categoria_id": categoria.id,
            "marca": "Sony",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["nombre_universal"] == "Auriculares Sony"
    assert body["categoria_id"] == categoria.id


def test_post_products_categoria_invalida_devuelve_400(api_client) -> None:
    response = api_client.post(
        "/api/v1/products",
        json={"nombre_universal": "X", "categoria_id": 999},
    )

    assert response.status_code == 400
    assert "no existe" in response.json()["detail"]


def test_post_products_payload_invalido_devuelve_422(api_client) -> None:
    response = api_client.post(
        "/api/v1/products",
        json={"nombre_universal": ""},
    )

    assert response.status_code == 422


def test_get_products_con_filtros_y_total(api_client, db_session) -> None:
    from src.models.categoria import Categoria
    from src.schemas.producto_canonico import ProductoCanonicoCreate
    from src.services import product_service

    cat_a = Categoria(nombre="Alimentos y Bebidas")
    cat_b = Categoria(nombre="Moda")
    db_session.add_all([cat_a, cat_b])
    db_session.commit()

    product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Coca Cola 2L",
            categoria_id=cat_a.id,
        ),
    )
    product_service.create_product(
        db_session,
        ProductoCanonicoCreate(
            nombre_universal="Auriculares",
            categoria_id=cat_b.id,
        ),
    )

    todos = api_client.get("/api/v1/products")
    assert todos.status_code == 200
    assert todos.json()["total"] == 2
    assert len(todos.json()["items"]) == 2

    filtrados = api_client.get(
        "/api/v1/products",
        params={"category_id": cat_a.id},
    )
    assert filtrados.json()["total"] == 1
    assert filtrados.json()["items"][0]["nombre_universal"] == "Coca Cola 2L"

    buscados = api_client.get("/api/v1/products", params={"search": "auric"})
    assert buscados.json()["total"] == 1


def test_get_product_por_id_y_404(api_client, db_session) -> None:
    from src.schemas.producto_canonico import ProductoCanonicoCreate
    from src.services import product_service

    producto = product_service.create_product(
        db_session,
        ProductoCanonicoCreate(nombre_universal="Coca Cola 2L"),
    )

    ok = api_client.get(f"/api/v1/products/{producto.id}")
    assert ok.status_code == 200
    assert ok.json()["id"] == producto.id

    no_existe = api_client.get("/api/v1/products/99999")
    assert no_existe.status_code == 404


def test_patch_product_actualiza(api_client, db_session) -> None:
    from src.schemas.producto_canonico import ProductoCanonicoCreate
    from src.services import product_service

    producto = product_service.create_product(
        db_session,
        ProductoCanonicoCreate(nombre_universal="Nombre viejo"),
    )

    response = api_client.patch(
        f"/api/v1/products/{producto.id}",
        json={"nombre_universal": "Nombre nuevo", "marca": "Marca Nueva"},
    )

    assert response.status_code == 200
    assert response.json()["nombre_universal"] == "Nombre nuevo"
    assert response.json()["marca"] == "Marca Nueva"


def test_get_categories(api_client, db_session) -> None:
    from src.models.categoria import Categoria

    db_session.add(Categoria(nombre="Tecnologia"))
    db_session.commit()

    response = api_client.get("/api/v1/products/categories")
    assert response.status_code == 200
    assert response.json() == [
        {"id": response.json()[0]["id"], "nombre": "Tecnologia"},
    ]
