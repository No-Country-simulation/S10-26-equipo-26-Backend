"""Job de alertas (HU 2.4 + 3.5) — corre en cron.

    python -m scripts.run_alerts                    # ultimos 30 dias
    python -m scripts.run_alerts --days 7

1. detect_shrinkflation (idempotente: no duplica abiertas)
2. evaluate_outpace_devaluation en el rango

Sale con codigo 0 siempre que no haya error fatal (requisito cron Railway/GH).
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.session import SessionLocal
from src.services import alert_engine, shrinkflation_detector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("run_alerts")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_alerts")
    parser.add_argument("--days", type=int, default=30, help="ventana en dias")
    args = parser.parse_args(argv)

    end = date.today()
    start = end - timedelta(days=args.days)

    with SessionLocal() as db:
        try:
            creadas = shrinkflation_detector.detect_shrinkflation(db)
            logger.info("shrinkflation_alertas_nuevas=%d", len(creadas))
        except Exception:
            logger.exception("shrinkflation_fallo")
            return 1
        try:
            deval = alert_engine.evaluate_outpace_devaluation(
                db, start=start, end=end
            )
            logger.info(
                "outpace_alertas_nuevas=%d rango=%s..%s", len(deval), start, end
            )
        except Exception:
            logger.exception("outpace_fallo")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
