"""Propuesta automatica de mapeo por similitud (HU 1.4).

Normalizacion en paridad con `src/normalizers/strings.py` del repo Data
(mismo algoritmo, test de paridad en tests/services/test_matching_service.py).

Umbrales acordados (PLAN-AGIL HU 1.4):
- score >= 0.90 => banda `auto` (auto-sugiere)
- 0.75 <= score < 0.90 => banda `review` (revision manual)
"""

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError
from src.models.producto_canonico import ProductoCanonico
from src.models.store_product import StoreProduct
from src.models.tienda import Tienda

AUTO_THRESHOLD = 0.90
DEFAULT_THRESHOLD = 0.75


def normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFKD", str(text).lower())
    without_accents = "".join(
        char for char in lowered if not unicodedata.combining(char)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents)
    separated = re.sub(
        r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)",
        " ",
        without_punctuation,
    )
    return re.sub(r"\s+", " ", separated).strip()


def tokens(text: str) -> list[str]:
    normalized = normalize(text)
    return normalized.split() if normalized else []


def similarity(text_a: str, text_b: str) -> float:
    score = fuzz.token_sort_ratio(normalize(text_a), normalize(text_b))
    return round(score / 100.0, 4)


@dataclass(frozen=True)
class MatchSuggestion:
    store_product: StoreProduct
    product: ProductoCanonico
    score: float
    band: str  # "auto" >= 0.90 | "review" 0.75..0.90


def _best_candidate_score(
    sp: StoreProduct,
    product: ProductoCanonico,
) -> float:
    candidatos_sp = [sp.nombre_crudo]
    if sp.marca_cruda:
        candidatos_sp.append(f"{sp.marca_cruda} {sp.nombre_crudo}")

    candidatos_p = [product.nombre_universal]
    if product.marca:
        candidatos_p.append(f"{product.marca} {product.nombre_universal}")

    return max(
        similarity(a, b)
        for a in candidatos_sp
        for b in candidatos_p
    )


def suggest_matches(
    db: Session,
    tienda_id: int,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[MatchSuggestion]:
    if db.get(Tienda, tienda_id) is None:
        raise NotFoundError(f"tienda {tienda_id} no encontrada")

    store_products = list(
        db.scalars(
            select(StoreProduct)
            .where(StoreProduct.tienda_id == tienda_id)
            .order_by(StoreProduct.id),
        ),
    )
    productos = list(db.scalars(select(ProductoCanonico)))
    if not store_products or not productos:
        return []

    sugerencias: list[MatchSuggestion] = []
    for sp in store_products:
        mejor: tuple[float, ProductoCanonico] | None = None
        for product in productos:
            score = _best_candidate_score(sp, product)
            if mejor is None or score > mejor[0]:
                mejor = (score, product)

        if mejor is None or mejor[0] < threshold:
            continue

        band = "auto" if mejor[0] >= AUTO_THRESHOLD else "review"
        sugerencias.append(
            MatchSuggestion(
                store_product=sp,
                product=mejor[1],
                score=mejor[0],
                band=band,
            ),
        )

    sugerencias.sort(key=lambda s: s.score, reverse=True)
    return sugerencias
