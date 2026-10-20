import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db.session import SessionLocal
from src.models import Product, Store


def run_seed() -> None:
    with SessionLocal() as session:
        existing = session.scalar(select(Store).limit(1))
        if existing is not None:
            print("Seed skipped: stores already exist")
            return

        stores = [
            Store(
                name="Store A",
                base_url="https://example-store-a.com",
                country_code="CL",
                currency_code="CLP",
            ),
            Store(
                name="Store B",
                base_url="https://example-store-b.com",
                country_code="CL",
                currency_code="CLP",
            ),
        ]
        session.add_all(stores)

        products = [
            Product(
                name="Café molido 500 g",
                brand="Marca Demo",
                category="Alimentos",
                reference_unit="500 g",
            ),
            Product(
                name='Smart TV 55"',
                brand="Marca Demo",
                category="Electrodomésticos",
                reference_unit="1 unidad",
            ),
            Product(
                name="Arroz 1 kg",
                brand="Marca Demo",
                category="Alimentos",
                reference_unit="1 kg",
            ),
            Product(
                name="Auriculares inalámbricos",
                brand="Marca Demo",
                category="Electrónica",
                reference_unit="1 unidad",
            ),
            Product(
                name="Zapatillas running",
                brand="Marca Demo",
                category="Moda",
                reference_unit="1 par",
            ),
        ]
        session.add_all(products)
        session.commit()
        print("Seed completed: 2 stores, 5 products")


if __name__ == "__main__":
    run_seed()
