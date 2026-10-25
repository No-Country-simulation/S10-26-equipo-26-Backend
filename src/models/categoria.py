from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("nombre", name="categorias_nombre_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
