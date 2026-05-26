from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class PriceVariationBetweenDatesRead(BaseModel):
    material_id: int
    material_nombre: str
    unidad_base: str
    fecha_desde_solicitada: date
    fecha_hasta_solicitada: date
    fecha_desde_usada: date
    fecha_hasta_usada: date
    precio_desde: Decimal
    precio_hasta: Decimal
    variacion_porcentual: Decimal


class ForecastMetricasRead(BaseModel):
    folds: int
    mae: Decimal
    mape: Decimal
    efectividad_informal: Decimal


class ForecastPuntoRead(BaseModel):
    fecha: date
    precio_proyectado: Decimal
    precio_optimista: Decimal | None = None
    precio_pesimista: Decimal | None = None
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


CommercialMarginScope = Literal["GLOBAL", "MATERIAL", "PRODUCT"]


class CommercialMarginBase(BaseModel):
    scope: CommercialMarginScope
    material_id: int | None = None
    presentation_id: int | None = None
    product_key: str | None = Field(default=None, max_length=200)
    margen_ganancia_pct: Decimal = Field(ge=0, decimal_places=2)
    activo: bool = True

    @model_validator(mode="after")
    def validate_scope(self) -> "CommercialMarginBase":
        if self.scope == "GLOBAL":
            if any(value is not None for value in (self.material_id, self.presentation_id, self.product_key)):
                raise ValueError("El margen GLOBAL no debe tener material_id, presentation_id ni product_key.")
        elif self.scope == "MATERIAL":
            if self.material_id is None:
                raise ValueError("El margen MATERIAL requiere material_id.")
            if self.presentation_id is not None or self.product_key is not None:
                raise ValueError("El margen MATERIAL no debe tener presentation_id ni product_key.")
        elif self.scope == "PRODUCT":
            if self.material_id is None:
                raise ValueError("El margen PRODUCT requiere material_id.")
            if self.presentation_id is None and not self.product_key:
                raise ValueError("El margen PRODUCT requiere presentation_id o product_key.")
        return self


class CommercialMarginCreate(CommercialMarginBase):
    pass


class CommercialMarginUpdate(BaseModel):
    scope: CommercialMarginScope | None = None
    material_id: int | None = None
    presentation_id: int | None = None
    product_key: str | None = Field(default=None, max_length=200)
    margen_ganancia_pct: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    activo: bool | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "CommercialMarginUpdate":
        if self.scope == "GLOBAL":
            if any(value is not None for value in (self.material_id, self.presentation_id, self.product_key)):
                raise ValueError("El margen GLOBAL no debe tener material_id, presentation_id ni product_key.")
        elif self.scope == "MATERIAL":
            if self.material_id is None:
                raise ValueError("El margen MATERIAL requiere material_id.")
            if self.presentation_id is not None or self.product_key is not None:
                raise ValueError("El margen MATERIAL no debe tener presentation_id ni product_key.")
        elif self.scope == "PRODUCT":
            if self.material_id is None:
                raise ValueError("El margen PRODUCT requiere material_id.")
            if self.presentation_id is None and not self.product_key:
                raise ValueError("El margen PRODUCT requiere presentation_id o product_key.")
        return self


class CommercialMarginRead(BaseModel):
    id: int
    scope: CommercialMarginScope
    material_id: int | None
    presentation_id: int | None
    product_key: str | None
    margen_ganancia_pct: Decimal
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommercialPriceRead(BaseModel):
    material_id: int
    material_key: str
    presentation_id: int | None
    product_key: str | None
    costo_base_actual: Decimal | None
    costo_base_proyectado: Decimal | None
    margen_ganancia_pct: Decimal | None
    origen_margen: CommercialMarginScope | Literal["SIN_MARGEN"]
    precio_final_actual: Decimal | None
    precio_final_proyectado: Decimal | None
    ganancia_unitaria_actual: Decimal | None
    ganancia_unitaria_proyectada: Decimal | None
    advertencias: list[str]


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
    precio_actual: Decimal | None = None
    precio_proyectado_horizonte: Decimal | None = None
    precio_proyectado_optimista: Decimal | None = None
    precio_proyectado_pesimista: Decimal | None = None
    cantidad_objetivo: Decimal | None = None
    impacto_economico_estimado: Decimal | None = None
    mape: Decimal | None = None
    umbral_decision_pct: Decimal | None = None
    supera_umbral_decision: bool = False
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
    diferencia_vs_mejor_ars: Decimal
    diferencia_vs_mejor_pct: Decimal
    riesgo: str
    descripcion: str

    model_config = ConfigDict(from_attributes=True)


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
    umbral_decision_pct: Decimal
    ventaja_significativa: bool
    justificacion: str
    advertencias: list[str]


class PurchaseTemporalSimulationCreate(BaseModel):
    horizontes_meses: list[int] = Field(default=[3, 6, 12], min_length=2)
    cantidad_objetivo: Decimal = Field(gt=0, decimal_places=4)
    porcentaje_compra_inmediata: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        le=1,
        decimal_places=4,
    )

    @model_validator(mode="after")
    def validate_horizontes(self):
        if any(horizonte < 1 or horizonte > 12 for horizonte in self.horizontes_meses):
            raise ValueError("Cada horizonte_meses debe estar entre 1 y 12")
        if len(set(self.horizontes_meses)) != len(self.horizontes_meses):
            raise ValueError("horizontes_meses no puede tener valores duplicados")
        return self


class PurchaseTemporalSimulationRead(BaseModel):
    material_id: int
    material_key: str
    cantidad_objetivo: Decimal
    porcentaje_compra_inmediata: Decimal
    simulaciones: list[PurchaseStrategyComparisonRead]


class PurchaseOptimizationMaterialCreate(BaseModel):
    material_id: int
    cantidad_objetivo: Decimal = Field(gt=0, decimal_places=4)
    criticidad: Literal["alta", "media", "baja"]
    porcentaje_minimo_compra_inmediata: Decimal | None = Field(default=None, ge=0, le=1, decimal_places=4)


class PurchaseOptimizationCreate(BaseModel):
    presupuesto_total: Decimal = Field(gt=0, decimal_places=2)
    horizonte_meses: int = Field(default=3, ge=1, le=12)
    materiales: list[PurchaseOptimizationMaterialCreate] = Field(min_length=1)


class PurchaseOptimizationItemRead(BaseModel):
    material_id: int
    material_key: str
    cantidad_objetivo: Decimal
    cantidad_recomendada_comprar_ahora: Decimal
    cantidad_recomendada_postergar: Decimal
    precio_actual: Decimal
    precio_proyectado_horizonte: Decimal
    costo_compra_ahora: Decimal
    costo_futuro_estimado: Decimal
    ahorro_unitario_estimado: Decimal
    ahorro_total_estimado: Decimal
    impacto_economico_pct: Decimal
    accion_recomendada: Literal["COMPRAR_AHORA", "POSTERGAR", "COMPRA_PARCIAL"]
    criticidad: str
    peso_criticidad: Decimal
    confiabilidad: str


class PurchaseOptimizationRead(BaseModel):
    presupuesto_total: Decimal
    presupuesto_utilizado: Decimal
    presupuesto_restante: Decimal
    horizonte_meses: int
    estado_optimizacion: str
    items: list[PurchaseOptimizationItemRead]
    ahorro_total_estimado: Decimal
    justificacion: str
    advertencias: list[str]


class OperationalPurchaseRecommendationCreate(PurchaseOptimizationCreate):
    pass


class OperationalPurchaseRecommendationItemRead(BaseModel):
    material_id: int
    material_key: str
    accion_recomendada: Literal["COMPRAR_AHORA", "POSTERGAR", "COMPRA_PARCIAL"]
    cantidad_comprar_ahora: Decimal
    cantidad_postergar: Decimal
    impacto_economico_estimado: Decimal
    impacto_economico_pct: Decimal
    confianza: str
    criticidad: str
    recomendacion_simple: Literal["COMPRAR_AHORA", "ESPERAR", "MONITOREAR"]
    mejor_estrategia: Literal["COMPRAR_AHORA", "ESPERAR_AL_HORIZONTE", "COMPRA_PARCIAL"]
    ventaja_estrategia_significativa: bool
    explicacion: str


class AlertaRead(BaseModel):
    id: int
    material_id: int | None
    tipo: str
    prioridad: str
    titulo: str
    mensaje: str
    data_context: str | None
    leida: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertaBatchUpdate(BaseModel):
    alerta_ids: list[int]
    leida: bool
