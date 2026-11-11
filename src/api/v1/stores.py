from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.tienda import Tienda
from src.schemas.tienda import TiendaRead

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[TiendaRead])
def list_stores(db: DbSession) -> list[TiendaRead]:
    """Listado de tiendas (contrato consumido por el Front: catalogService.getStores)."""
    tiendas = db.scalars(select(Tienda).order_by(Tienda.id))
    return [TiendaRead.model_validate(t) for t in tiendas]
