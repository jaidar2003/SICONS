from datetime import datetime
from decimal import Decimal

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


class FuenteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    tipo_fuente: str | None = Field(default=None, max_length=50)
    descripcion: str | None = None


class FuenteRead(FuenteCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
