from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Tienda(Base):
    __tablename__ = "tiendas"
    __table_args__ = (UniqueConstraint("nombre", name="tiendas_nombre_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    url_base: Mapped[str | None] = mapped_column(String(255))
