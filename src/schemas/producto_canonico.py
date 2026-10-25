from pydantic import BaseModel, ConfigDict


class ProductoCanonicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_universal: str
    categoria_id: int | None = None
    unidad_medida: str | None = None
    marca: str | None = None


class ProductoCanonicoCreate(BaseModel):
    nombre_universal: str
    categoria_id: int | None = None
    unidad_medida: str | None = None
    marca: str | None = None
