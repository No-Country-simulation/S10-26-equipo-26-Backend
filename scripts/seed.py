import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db.session import SessionLocal
from src.models import Categoria, ProductoCanonico, Tienda

CATEGORIAS = [
    "Alimentos y Bebidas",
    "Cuidado e Higiene Personal",
    "Tecnología",
    "Hogar y Limpieza",
    "Moda",
]

TIENDAS = [
    ("Carrefour", "https://www.carrefour.com.ar/"),
    ("Cetrogar", "https://www.cetrogar.com.ar/"),
    ("Coto", "https://www.coto.com.ar/"),
]

PRODUCTOS = [
    ("Arroz Blanco", 1, "1 kg", ""),
    ("Aceite de Girasol ", 1, "1,5 L", "Natura"),
    ("Yerba Mate ", 1, "500 G", "Playadito"),
    ("Leche Entera", 1, "1 L", "Larga Vida "),
    ("Crema Dental ", 2, "90 gr", "Crema dental "),
    ("Papel Higiénico ", 2, "4 Rollos", "Higienol"),
    ("Jabón Corporal x3", 2, "90 g ", "Dove"),
    ("Smart TV 50''", 3, "unidad", "Samsung "),
    ("Celular Smartphone 128GB", 3, "unidad", "Motorola"),
    ("Licuadora 2 Velocidades", 3, "unidad", None),
    ("Detergente en Polvo", 4, "800g", None),
    ("Shampoo", 4, "340 ml", None),
    ("Remera básica ", 5, "unidad", None),
    ("Medias ", 5, "unidad", None),
    (" Zapatillas urbanas", 5, "par", "Adidas "),
]


def run_seed() -> None:
    """Seed idempotente: replica el catalogo de la BD (Railway). Salta si ya hay tiendas."""
    with SessionLocal() as session:
        existing = session.scalar(select(Tienda).limit(1))
        if existing is not None:
            print("Seed skipped: tiendas already exist")
            return

        for nombre in CATEGORIAS:
            session.add(Categoria(nombre=nombre))
        session.flush()

        for nombre, url in TIENDAS:
            session.add(Tienda(nombre=nombre, url_base=url))
        session.flush()

        for nombre, categoria_id, unidad, marca in PRODUCTOS:
            session.add(
                ProductoCanonico(
                    nombre_universal=nombre,
                    categoria_id=categoria_id,
                    unidad_medida=unidad,
                    marca=marca,
                )
            )
        session.commit()
        print(
            f"Seed completed: {len(CATEGORIAS)} categorias, "
            f"{len(TIENDAS)} tiendas, {len(PRODUCTOS)} productos"
        )


if __name__ == "__main__":
    run_seed()
