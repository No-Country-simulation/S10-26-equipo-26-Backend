from pydantic import BaseModel, ConfigDict


class TiendaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    url_base: str | None = None


class TiendaCreate(BaseModel):
    nombre: str
    url_base: str | None = None
