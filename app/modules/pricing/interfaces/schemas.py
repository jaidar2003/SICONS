from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PrecioHistoricoCreate(BaseModel):
    material_id: int
    presentacion_id: int | None = None
    fuente_id: int | None = None
    fecha: date
    precio_original: Decimal = Field(ge=0, decimal_places=2)
    moneda: str = Field(default="ARS", min_length=1, max_length=10)
    numero_comprobante: str | None = Field(default=None, max_length=50)
    origen_dato: str = Field(default="REAL", min_length=1, max_length=20)
    metodo_estimacion: str | None = Field(default=None, max_length=50)
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
    precio_equivalente_25kg: Decimal | None = None
    precio_equivalente_50kg: Decimal | None = None
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


class ForecastSelectionRead(BaseModel):
    material_key: str | None = None
    modelo_resuelto: str
    regresores_resueltos: list[str]
    mape_referencia: Decimal | None = None
    mae_referencia: Decimal | None = None
    folds: int | None = None
    confiabilidad: str
    origen_decision: str
    justificacion: str
    no_calibrado: bool
    advertencia: str | None = None


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
    seleccion_modelo: ForecastSelectionRead | None = None


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


class ExternalIndexValueRead(BaseModel):
    id: int
    source_name: str
    series_id: str
    date: date
    value: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalIndexSyncRequest(BaseModel):
    source_name: str = Field(min_length=1, max_length=50)
    series_id: str = Field(min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None


class ExternalIndexSyncResponse(BaseModel):
    source_name: str
    series_id: str
    inserted: int
    updated: int
    unchanged: int


class PriceImputationRequest(BaseModel):
    start_date: date
    end_date: date
    index_series_id: str = Field(min_length=1, max_length=100)
    source_name: str = Field(min_length=1, max_length=50)
    metodo_estimacion: str = Field(min_length=1, max_length=50)


class PriceImputationResponse(BaseModel):
    material_id: int
    source_name: str
    series_id: str
    metodo_estimacion: str
    inserted: int
    updated: int
    skipped_real_months: int
    generated_months: list[date]


class PurchaseRecommendationCreate(BaseModel):
    horizonte_meses: int = Field(default=3, ge=1, le=12)
    criticidad: Literal["alta", "media", "media-baja", "baja"]
    cantidad_objetivo: Decimal = Field(gt=0, decimal_places=4)


class PurchaseRecommendationRead(BaseModel):
    material_id: int
    material_key: str
    horizonte_meses: int
    decision: Literal["COMPRAR_AHORA", "ESPERAR", "MONITOREAR"]
    variacion_esperada_pct: Decimal | None = None
    confiabilidad: str
    criticidad: str
    justificacion: str
    advertencias: list[str]


class PurchaseStrategyComparisonCreate(BaseModel):
    horizonte_meses: int = Field(default=3, ge=1, le=12)
    cantidad_objetivo: Decimal = Field(gt=0, decimal_places=4)
    porcentaje_compra_inmediata: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        le=1,
        decimal_places=4,
    )


class PurchaseStrategyRead(BaseModel):
    nombre: Literal["COMPRAR_AHORA", "ESPERAR_AL_HORIZONTE", "COMPRA_PARCIAL"]
    costo_estimado: Decimal
    riesgo: str
    descripcion: str


class PurchaseStrategyComparisonRead(BaseModel):
    material_id: int
    material_key: str
    horizonte_meses: int
    cantidad_objetivo: Decimal
    porcentaje_compra_inmediata: Decimal
    precio_actual: Decimal
    precio_proyectado_horizonte: Decimal
    variacion_esperada_pct: Decimal
    confiabilidad: str
    estrategias: list[PurchaseStrategyRead]
    mejor_estrategia: Literal["COMPRAR_AHORA", "ESPERAR_AL_HORIZONTE", "COMPRA_PARCIAL"]
    ahorro_estimado: Decimal
    justificacion: str
    advertencias: list[str]
