from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PresentacionCreate(BaseModel):
    material_id: int
    nombre_presentacion: str = Field(min_length=1, max_length=100)
    cantidad_base: Decimal = Field(gt=0, decimal_places=4)
    unidad_presentacion: str = Field(min_length=1, max_length=20)
    activa: bool = True


class PresentacionRead(PresentacionCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
