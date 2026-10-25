from pydantic import BaseModel, ConfigDict


class CategoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class CategoriaCreate(BaseModel):
    nombre: str
