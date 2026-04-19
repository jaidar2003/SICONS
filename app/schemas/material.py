from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    categoria: str | None = Field(default=None, max_length=100)
    marca: str | None = Field(default=None, max_length=100)
    unidad_base: str = Field(min_length=1, max_length=20)
    descripcion: str | None = None
    activo: bool = True


class MaterialRead(MaterialCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
