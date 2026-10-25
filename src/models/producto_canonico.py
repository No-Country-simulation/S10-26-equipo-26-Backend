from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ProductoCanonico(Base):
    __tablename__ = "productos_canonicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_universal: Mapped[str] = mapped_column(String(255))
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))
    unidad_medida: Mapped[str | None] = mapped_column(String(50))
    marca: Mapped[str | None] = mapped_column(Text)
