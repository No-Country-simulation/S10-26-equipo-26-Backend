from pydantic import BaseModel, ConfigDict, Field


class ProductoCanonicoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_universal: str
    categoria_id: int | None = None
    unidad_medida: str | None = None
    marca: str | None = None


class ProductoCanonicoCreate(BaseModel):
    nombre_universal: str = Field(min_length=1, max_length=255)
    categoria_id: int | None = None
    unidad_medida: str | None = Field(default=None, max_length=50)
    marca: str | None = None


class ProductoCanonicoUpdate(BaseModel):
    nombre_universal: str | None = Field(default=None, min_length=1, max_length=255)
    categoria_id: int | None = None
    unidad_medida: str | None = Field(default=None, max_length=50)
    marca: str | None = None


class ProductoCanonicoList(BaseModel):
    items: list[ProductoCanonicoRead]
    total: int
