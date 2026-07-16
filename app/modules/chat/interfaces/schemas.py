from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChatHistoryMessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatQueryCreate(BaseModel):
    pregunta: str = Field(min_length=1, max_length=1000)
    material_id: int | None = Field(default=None, ge=1)
    conversation_id: int | None = Field(default=None, ge=1)
    horizonte_meses: int | None = Field(default=None, ge=1, le=12)
    historial: list[ChatHistoryMessageCreate] = Field(default_factory=list, max_length=8)


class ChatVisualizationRead(BaseModel):
    tipo: Literal["PRICE_HISTORY", "FORECAST", "PRICE_HISTORY_FORECAST"]
    material_id: int = Field(ge=1)
    horizonte_meses: int | None = Field(default=None, ge=1, le=12)


class ChatSourceEvidenceRecordRead(BaseModel):
    fecha: date | None = None
    precio_normalizado: str | None = None
    unidad_base: str | None = None
    fuente: str | None = None
    comprobante: str | None = None


class ChatSourceEvidenceRead(BaseModel):
    source: str
    records: list[ChatSourceEvidenceRecordRead] = Field(default_factory=list)


class ChatResponseRead(BaseModel):
    aceptada: bool
    respuesta: str
    proveedor_utilizado: bool
    proveedor_ia: str | None = None
    fallback_usado: bool = False
    tipo_intencion: Literal["HISTORICO", "FORECAST", "RECOMENDACION", "PRESUPUESTO", "CATALOGO", "ADMIN", "FUERA_ALCANCE"] | None = None
    contexto_usado: bool = False
    fuentes_recuperadas: list[str] = Field(default_factory=list)
    fuentes_evidencia: list[ChatSourceEvidenceRead] = Field(default_factory=list)
    material_resuelto_id: int | None = None
    material_resuelto: str | None = None
    material_resolution_source: Literal["pregunta", "contexto", "seleccionado"] | None = None
    horizonte_resuelto: int | None = None
    visualizacion_sugerida: ChatVisualizationRead | None = None
    conversation_id: int | None = None


class ChatConversationCreate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=160)


class ChatConversationUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=160)
    archived: bool | None = None


class ChatConversationRead(BaseModel):
    id: int
    titulo: str
    material_actual_id: int | None = None
    horizonte_actual: int | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    ultimo_mensaje: str | None = None


class ChatMessageRead(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    tipo_intencion: Literal["HISTORICO", "FORECAST", "RECOMENDACION", "PRESUPUESTO", "CATALOGO", "ADMIN", "FUERA_ALCANCE"] | None = None
    contexto_usado: bool | None = None
    fuentes_recuperadas: list[str] = Field(default_factory=list)
    fuentes_evidencia: list[ChatSourceEvidenceRead] = Field(default_factory=list)
    material_resuelto_id: int | None = None
    material_resuelto: str | None = None
    material_resolution_source: Literal["pregunta", "contexto", "seleccionado"] | None = None
    horizonte_resuelto: int | None = None
    visualizacion_sugerida: ChatVisualizationRead | None = None
    proveedor_ia: str | None = None
    fallback_usado: bool | None = None
    created_at: datetime


class ChatAuditLogRead(BaseModel):
    id: int
    created_at: datetime
    usuario_id: int | None = None
    username: str | None = None
    pregunta: str | None = None
    respuesta: str | None = None
    aceptada: bool | None = None
    tipo_intencion: Literal["HISTORICO", "FORECAST", "RECOMENDACION", "PRESUPUESTO", "CATALOGO", "ADMIN", "FUERA_ALCANCE"] | None = None
    contexto_usado: bool | None = None
    fuentes_recuperadas: list[str] = Field(default_factory=list)
    material_resuelto: str | None = None
    material_resolution_source: str | None = None
    horizonte_resuelto: int | None = None
    proveedor_ia: str | None = None
    fallback_usado: bool | None = None
    respuesta_deterministica: bool | None = None
    respuesta_alternativa: bool | None = None
    tipo_fallo: str | None = None
    etapa_fallida: str | None = None
    duration_ms: int | None = None
    interpretation_ms: int | None = None
    backend_ms: int | None = None
    provider_ms: int | None = None
    ip_address: str | None = None


class ChatDeterminismGroupRead(BaseModel):
    pregunta_normalizada: str
    muestra: int
    score: float
    campos_estables: list[str]
    campos_variables: list[str]
    pregunta_ejemplo: str | None = None
    tipo_intencion: str | None = None
    material_resuelto: str | None = None
    horizonte_resuelto: int | None = None
    fuentes_recuperadas: list[str] = Field(default_factory=list)


class ChatDeterminismReportRead(BaseModel):
    total_consultas: int
    grupos_repetidos: int
    consultas_evaluadas: int
    score_promedio: float | None = None
    campos_evaluados: list[str]
    grupos: list[ChatDeterminismGroupRead]


class ChatAuditMetricsRead(BaseModel):
    total_consultas: int
    consultas_fuera_de_alcance: int
    tasa_fallback: float
    latencia_promedio_ms: float | None = None
    latencia_p95_ms: float | None = None
    consultas_por_intencion: dict[str, int]
    usuarios_unicos: int


class ChatDeterminismCanonicalItemRead(BaseModel):
    pregunta: str
    muestra: int
    score: float
    cumple_expectativa: bool
    tipo_intencion_esperada: str
    tipo_intencion_observada: str | None = None
    material_esperado: str | None = None
    material_observado: str | None = None
    horizonte_esperado: int | None = None
    horizonte_observado: int | None = None
    fuentes_esperadas: list[str] = Field(default_factory=list)
    fuentes_observadas: list[str] = Field(default_factory=list)
    campos_estables: list[str] = Field(default_factory=list)
    campos_variables: list[str] = Field(default_factory=list)


class ChatDeterminismCanonicalReportRead(BaseModel):
    total_casos: int
    casos_con_evidencia: int
    cobertura: float
    score_promedio: float | None = None
    casos: list[ChatDeterminismCanonicalItemRead]


class ChatProviderConfigRead(BaseModel):
    proveedor_activo: str
    modelo_facultad: str | None = None
    modelo_claude: str | None = None
    fallback_habilitado: bool = True


class ChatProviderStatusRead(BaseModel):
    proveedor_activo: str
    modelo_activo: str | None = None
    fallback_habilitado: bool = True
    proveedor_fallback: str | None = None
    modelo_fallback: str | None = None
    estado_ultima_llamada: Literal["sin_datos", "ok", "error"] = "sin_datos"
    proveedor_ultima_llamada: str | None = None
    fallback_ultima_llamada: bool | None = None
    error_ultima_llamada: str | None = None


class ChatProviderConfigUpdate(BaseModel):
    proveedor_activo: Literal["facultad", "claude"]
    modelo_facultad: str | None = Field(default=None, max_length=200)
    modelo_claude: str | None = Field(default=None, max_length=200)


class CommercialNeedCreate(BaseModel):
    necesidad: str = Field(min_length=1, max_length=1500)


class CommercialNeedInterpretationRead(BaseModel):
    solicitud_original: str
    material_id: int | None = None
    producto_nombre: str | None = None
    cantidad: Decimal | None = None
    fase_obra: str | None = None
    fecha_objetivo_uso: date | None = None
    horizonte_meses: int | None = None
    presupuesto_maximo: Decimal | None = None
    tolerancia_riesgo: Literal["baja", "media", "alta"]
    datos_faltantes: list[str]
    requiere_validacion: bool = True
    requiere_confirmacion: bool = True
    proveedor_utilizado: bool = True
    proveedor_ia: str | None = None
    fallback_usado: bool = False


class CommercialProposalCreate(BaseModel):
    material_id: int = Field(ge=1)
    cantidad: Decimal = Field(gt=0, decimal_places=4)
    fase_obra: Literal["estructura", "terminaciones", "impermeabilizacion", "general"]
    tolerancia_riesgo: Literal["baja", "media", "alta"] = "media"
    fecha_objetivo_uso: date | None = None
    horizonte_meses: int | None = Field(default=None, ge=1, le=12)
    presupuesto_maximo: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    solicitud_original: str | None = Field(default=None, max_length=1500)

    @model_validator(mode="after")
    def validate_horizonte_o_fecha(self):
        if self.fecha_objetivo_uso is None and self.horizonte_meses is None:
            raise ValueError("Debe informar fecha_objetivo_uso u horizonte_meses")
        if self.fecha_objetivo_uso is not None and self.horizonte_meses is not None:
            self.horizonte_meses = None
        return self


class CommercialProposalRead(BaseModel):
    material_id: int
    producto_nombre: str
    cantidad: Decimal
    fase_obra: str
    fecha_objetivo_uso: date | None = None
    fecha_base_calculo: date | None = None
    horizonte_meses: int
    tolerancia_riesgo: str
    presupuesto_maximo: Decimal | None = None
    precio_unitario_actual: Decimal | None = None
    total_actual: Decimal | None = None
    precio_unitario_proyectado: Decimal | None = None
    total_proyectado: Decimal | None = None
    diferencia_estimada: Decimal | None = None
    decision: str
    confiabilidad: str
    mape: Decimal | None = None
    justificacion: str
    propuesta: str
    advertencias: list[str]
    fuente_decision: str = "backend_deterministico"
    propuesta_generada_por: str = "llm_validado"
    proveedor_utilizado: bool = True
    proveedor_ia: str | None = None
    fallback_usado: bool = False
