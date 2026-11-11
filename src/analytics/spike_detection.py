"""Deteccion de picos de precio: mediana movil + MAD (HU 3.4).

Regla: para cada punto se calcula la mediana de la ventana precedente
(`window`) y la MAD (median absolute deviation) de esa ventana.
Hay pico si `|x - mediana| > k * MAD * 1.4826` (1.4826 => estimator
consistente de sigma bajo normalidad). Con MAD = 0 se compara exactitud:
cualquier punto distinto de la mediana es pico.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median

MAD_TO_SIGMA = Decimal("1.4826")
DEFAULT_K = Decimal(3)


@dataclass(frozen=True)
class PriceSpike:
    date: date
    value: Decimal
    rolling_median: Decimal
    mad: Decimal
    score: Decimal


def _mad(valores: list[Decimal], center: Decimal) -> Decimal:
    desviaciones = [abs(v - center) for v in valores]
    return Decimal(str(median(desviaciones)))


def detect_spikes(
    serie: list[tuple[date, Decimal]],
    window: int = 5,
    k: Decimal | float | str = DEFAULT_K,
) -> list[PriceSpike]:
    """Serie ordenada de (fecha, valor). Devuelve los picos detectados.

    Los primeros `window` puntos no se evaluan (sin ventana completa).
    """
    if window < 2:
        raise ValueError("window debe ser >= 2")
    k_dec = Decimal(str(k))
    if k_dec <= 0:
        raise ValueError("k debe ser > 0")

    ordenada = sorted(serie, key=lambda par: par[0])
    picos: list[PriceSpike] = []

    for i in range(window, len(ordenada)):
        ventana = [valor for _, valor in ordenada[i - window : i]]
        centro = Decimal(str(median(ventana)))
        mad = _mad(ventana, centro)
        dia, valor = ordenada[i]

        if mad == 0:
            es_pico = valor != centro
            score = Decimal(0) if not es_pico else abs(valor - centro)
        else:
            umbral = k_dec * mad * MAD_TO_SIGMA
            desvio = abs(valor - centro)
            es_pico = desvio > umbral
            score = (desvio / umbral).quantize(Decimal("0.01")) if umbral else Decimal(0)

        if es_pico:
            picos.append(
                PriceSpike(
                    date=dia,
                    value=valor,
                    rolling_median=centro,
                    mad=mad,
                    score=score,
                ),
            )

    return picos
