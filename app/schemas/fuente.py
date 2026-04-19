from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FuenteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    tipo_fuente: str | None = Field(default=None, max_length=50)
    descripcion: str | None = None


class FuenteRead(FuenteCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
