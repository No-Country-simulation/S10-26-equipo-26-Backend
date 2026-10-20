from fastapi import APIRouter

from src.api.v1 import alerts, exchange_rates, health, indicators, prices, products

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(prices.router, prefix="/prices", tags=["prices"])
api_router.include_router(
    indicators.router,
    prefix="/indicators",
    tags=["indicators"],
)
api_router.include_router(
    exchange_rates.router,
    prefix="/exchange-rates",
    tags=["exchange-rates"],
)
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
