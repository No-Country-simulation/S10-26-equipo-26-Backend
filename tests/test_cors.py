"""CORS: el Front (otro origen) debe poder llamar a la API (SPEC §2.3)."""

FRONT_ORIGIN = "https://frontend-production-8b04.up.railway.app"


def test_cors_headers_para_origen_frontend(client) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": FRONT_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == FRONT_ORIGIN


def test_cors_preflight_options(client) -> None:
    response = client.options(
        "/api/v1/products",
        headers={
            "Origin": FRONT_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == FRONT_ORIGIN
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_origen_desconocido_sin_acao(client) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "https://evil.example.com"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
