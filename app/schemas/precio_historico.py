from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PrecioHistoricoCreate(BaseModel):
    material_id: int
    presentacion_id: int | None = None
    fuente_id: int | None = None
    fecha: date
    precio_original: Decimal = Field(ge=0, decimal_places=2)
    moneda: str = Field(default="ARS", min_length=1, max_length=10)
    observaciones: str | None = None


class PrecioHistoricoRead(PrecioHistoricoCreate):
    id: int
    precio_normalizado: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
