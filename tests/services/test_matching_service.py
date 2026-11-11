"""Tests de unidad: matching_service (HU 1.4) + paridad con Data."""

import pytest

from src.core.exceptions import NotFoundError
from src.models.producto_canonico import ProductoCanonico
from src.models.tienda import Tienda
from src.services import matching_service
from src.services.matching_service import normalize, similarity, tokens

# --- paridad con src/normalizers/strings.py del repo Data ---


def test_normalize_quita_tildes_y_puntuacion() -> None:
    assert normalize("Coca-Cola 500 ML") == "coca cola 500 ml"
    assert normalize("  Caf\u00e9  Instant\u00e1neo  ") == "cafe instantaneo"


def test_normalize_separa_digitos_de_letras() -> None:
    assert normalize("500ml") == "500 ml"


def test_tokens() -> None:
    assert tokens("Arroz Lucchetti 1 kg") == ["arroz", "lucchetti", "1", "kg"]
    assert tokens("") == []


def test_similarity_alta_para_el_mismo_producto() -> None:
    score = similarity("Coca Cola 500ml", "COCA-COLA 500 ml")
    assert score >= 0.90


def test_similarity_baja_para_productos_distintos() -> None:
    score = similarity("Coca Cola 500ml", "Agua Villavicencio 2 l")
    assert score < 0.75


# --- sugerencias ---


@pytest.fixture
def tienda(db_session) -> Tienda:
    tienda = Tienda(nombre="Coto")
    db_session.add(tienda)
    db_session.commit()
    return tienda


def test_sugerencia_auto_band(db_session, tienda) -> None:
    from src.models.store_product import StoreProduct

    producto = ProductoCanonico(nombre_universal="Coca Cola 500 ml")
    db_session.add(producto)
    db_session.flush()
    db_session.add(
        StoreProduct(
            tienda_id=tienda.id,
            external_id="EXT-1",
            nombre_crudo="COCA-COLA 500 ml",
        )
    )
    db_session.commit()

    sugerencias = matching_service.suggest_matches(db_session, tienda.id)

    assert len(sugerencias) == 1
    s = sugerencias[0]
    assert s.score >= 0.90
    assert s.band == "auto"
    assert s.product.id == producto.id


def test_sugerencia_review_band(db_session, tienda) -> None:
    producto = ProductoCanonico(nombre_universal="Coca Cola 2 L")
    db_session.add(producto)
    db_session.flush()

    from src.models.store_product import StoreProduct

    db_session.add(
        StoreProduct(
            tienda_id=tienda.id,
            external_id="EXT-2",
            nombre_crudo="Coca Cola 2 litros",
        )
    )
    db_session.commit()

    sugerencias = matching_service.suggest_matches(db_session, tienda.id)

    assert len(sugerencias) == 1
    s = sugerencias[0]
    assert 0.75 <= s.score < 0.90
    assert s.band == "review"


def test_umbral_filtra_coincidencias_debiles(db_session, tienda) -> None:
    producto = ProductoCanonico(nombre_universal="Coca Cola 500 ml")
    db_session.add(producto)
    db_session.flush()

    from src.models.store_product import StoreProduct

    db_session.add(
        StoreProduct(
            tienda_id=tienda.id,
            external_id="EXT-3",
            nombre_crudo="Agua Villavicencio 2 l",
        )
    )
    db_session.commit()

    assert matching_service.suggest_matches(db_session, tienda.id) == []

    con_umbral_bajo = matching_service.suggest_matches(
        db_session,
        tienda.id,
        threshold=0.20,
    )
    assert len(con_umbral_bajo) == 1
    assert con_umbral_bajo[0].band == "review"


def test_tienda_inexistente_lanza_404(db_session) -> None:
    with pytest.raises(NotFoundError, match="tienda"):
        matching_service.suggest_matches(db_session, 9999)


def test_tienda_sin_datos_devuelve_vacio(db_session, tienda) -> None:
    assert matching_service.suggest_matches(db_session, tienda.id) == []


def test_elige_el_mejor_producto_canonico(db_session, tienda) -> None:
    coca = ProductoCanonico(nombre_universal="Coca Cola 500 ml")
    agua = ProductoCanonico(nombre_universal="Agua Villavicencio 2 l")
    db_session.add_all([coca, agua])
    db_session.flush()

    from src.models.store_product import StoreProduct

    db_session.add(
        StoreProduct(
            tienda_id=tienda.id,
            external_id="EXT-4",
            nombre_crudo="COCA-COLA 500 ml",
        )
    )
    db_session.commit()

    sugerencias = matching_service.suggest_matches(db_session, tienda.id)

    assert len(sugerencias) == 1
    assert sugerencias[0].product.id == coca.id


def test_considera_marca_en_el_score(db_session, tienda) -> None:
    producto = ProductoCanonico(
        nombre_universal="Yerba 1 kg",
        marca="Playadito",
    )
    db_session.add(producto)
    db_session.flush()

    from src.models.store_product import StoreProduct

    db_session.add(
        StoreProduct(
            tienda_id=tienda.id,
            external_id="EXT-5",
            nombre_crudo="Yerba 1kg",
            marca_cruda="Playadito",
        )
    )
    db_session.commit()

    sugerencias = matching_service.suggest_matches(db_session, tienda.id)

    assert len(sugerencias) == 1
    assert sugerencias[0].band == "auto"
