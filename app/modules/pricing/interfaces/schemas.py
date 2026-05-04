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
    numero_comprobante: str | None = Field(default=None, max_length=50)
    observaciones: str | None = None


class PrecioHistoricoRead(PrecioHistoricoCreate):
    id: int
    precio_normalizado: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrecioHistoricoRangoRead(BaseModel):
    desde: date | None
    hasta: date | None
    hoy: date
    tiene_fechas_futuras: bool
    hasta_real: date | None


class PuntoSeriePrecioRead(BaseModel):
    fecha: date
    precio_promedio_normalizado: Decimal
    unidad_base: str
    precio_equivalente_25kg: Decimal
    precio_equivalente_50kg: Decimal
    cantidad_registros: int
    cantidad_facturas: int
    fuentes: list[str]
    variacion_porcentual_anterior: Decimal | None
    es_anomalia: bool = False
    motivo_anomalia: str | None = None


class ForecastMetricasRead(BaseModel):
    folds: int
    mae: Decimal
    mape: Decimal
    efectividad_informal: Decimal


class ForecastPuntoRead(BaseModel):
    fecha: date
    precio_proyectado: Decimal
    precio_equivalente_25kg: Decimal | None = None
    precio_equivalente_50kg: Decimal | None = None


class ForecastResponseRead(BaseModel):
    material_id: int
    material_nombre: str
    unidad_base: str
    horizonte_meses: int
    modelo: str
    supuesto_regresores: str
    ultima_fecha_observada: date
    ultimo_precio_observado: Decimal
    metricas: ForecastMetricasRead
    puntos: list[ForecastPuntoRead]


class MaterialCriticidadItemCreate(BaseModel):
    material_id: int
    cantidad_requerida: Decimal = Field(gt=0, decimal_places=4)


class MaterialCriticidadCreate(BaseModel):
    horizonte_meses: int = Field(default=3, ge=1, le=12)
    alpha: Decimal = Field(default=Decimal("0.50"), ge=0, decimal_places=2)
    beta: Decimal = Field(default=Decimal("0.50"), ge=0, decimal_places=2)
    materiales: list[MaterialCriticidadItemCreate] = Field(min_length=1)


class MaterialCriticidadRead(BaseModel):
    material_id: int
    material_nombre: str
    unidad_base: str
    cantidad_requerida: Decimal
    precio_actual_normalizado: Decimal
    precio_proyectado_normalizado: Decimal
    impacto_absoluto: Decimal
    variacion_esperada_porcentual: Decimal
    impacto_normalizado: Decimal
    variacion_normalizada: Decimal
    criticidad: Decimal
    nivel_criticidad: str
    explicacion: str


class MaterialCriticidadResponseRead(BaseModel):
    horizonte_meses: int
    alpha: Decimal
    beta: Decimal
    materiales: list[MaterialCriticidadRead]
