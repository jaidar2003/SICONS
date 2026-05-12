from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user, require_admin
from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.application.commercial_margins import (
    actualizar_margen_comercial as actualizar_margen_comercial_service,
)
from app.modules.pricing.application.commercial_margins import (
    crear_margen_comercial as crear_margen_comercial_service,
)
from app.modules.pricing.application.commercial_margins import (
    listar_margenes_comerciales as listar_margenes_comerciales_service,
)
from app.modules.pricing.application.commercial_prices import (
    calcular_precio_comercial,
)
from app.modules.pricing.application.external_indices import list_external_indices, sync_external_index
from app.modules.pricing.application.forecast_service import (
    forecast_material,
)
from app.modules.pricing.application.historical_prices import (
    crear_precio_historico as crear_precio_historico_service,
)
from app.modules.pricing.application.historical_prices import (
    listar_precios_historicos as listar_precios_historicos_service,
)
from app.modules.pricing.application.historical_prices import (
    obtener_rango_precios_historicos as obtener_rango_precios_historicos_service,
)
from app.modules.pricing.application.imputation import impute_monthly_prices
from app.modules.pricing.application.priorities import priorizar_materiales_desde_forecast
from app.modules.pricing.application.purchase_optimization import (
    PurchaseOptimizationInputItem,
    optimizar_compra_con_presupuesto,
)
from app.modules.pricing.application.purchase_recommendations import recomendar_momento_compra
from app.modules.pricing.application.purchase_strategies import comparar_estrategias_compra
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios
from app.modules.pricing.domain.exceptions import MaterialNotFoundException
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import ExternalIndexValue, PrecioHistorico
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.modules.pricing.interfaces.schemas import (
    CommercialMarginCreate,
    CommercialMarginRead,
    CommercialMarginUpdate,
    CommercialPriceRead,
    ExternalIndexSyncRequest,
    ExternalIndexSyncResponse,
    ExternalIndexValueRead,
    ForecastResponseRead,
    MaterialCriticidadCreate,
    MaterialCriticidadResponseRead,
    PrecioHistoricoCreate,
    PrecioHistoricoRangoRead,
    PrecioHistoricoRead,
    PriceImputationRequest,
    PriceImputationResponse,
    PuntoSeriePrecioRead,
    PurchaseOptimizationCreate,
    PurchaseOptimizationRead,
    PurchaseRecommendationCreate,
    PurchaseRecommendationRead,
    PurchaseStrategyComparisonCreate,
    PurchaseStrategyComparisonRead,
)
from app.shared.database.session import get_db

router = APIRouter(tags=["precios historicos"])
USAR_SELECTOR_MODELO_FORECAST = True

@router.get("/precios-historicos/rango", response_model=PrecioHistoricoRangoRead)
def obtener_rango_precios_historicos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> PrecioHistoricoRangoRead:
    return PrecioHistoricoRangoRead(**obtener_rango_precios_historicos_service(db))


@router.get("/precios-historicos", response_model=list[PrecioHistoricoRead])
def listar_precios_historicos(
    material_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[PrecioHistorico]:
    return listar_precios_historicos_service(db, material_id=material_id, desde=desde, hasta=hasta)


@router.get("/indices-externos", response_model=list[ExternalIndexValueRead])
def listar_indices_externos(
    series_id: str | None = None,
    source_name: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[ExternalIndexValue]:
    return list_external_indices(
        db,
        series_id=series_id,
        source_name=source_name,
        start_date=desde,
        end_date=hasta,
    )


@router.post("/indices-externos/sync", response_model=ExternalIndexSyncResponse)
def sincronizar_indice_externo(
    payload: ExternalIndexSyncRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> ExternalIndexSyncResponse:
    result = sync_external_index(
        db,
        series_id=payload.series_id,
        source_name=payload.source_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return ExternalIndexSyncResponse(
        source_name=result.source_name,
        series_id=result.series_id,
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
    )


@router.get("/materiales/{material_id}/precios", response_model=list[PrecioHistoricoRead])
def listar_precios_por_material(
    material_id: int,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
) -> list[PrecioHistorico]:
    if material_repo.get_by_id(material_id) is None:
        raise MaterialNotFoundException(material_id)
    return pricing_repo.get_historical_prices(material_id, date(2000, 1, 1))


@router.get("/materiales/{material_id}/serie-precios", response_model=list[PuntoSeriePrecioRead])
def obtener_serie_precios_material(
    material_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    agrupacion: str = "dia",
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
):
    material = material_repo.get_by_id(material_id)
    if material is None:
        raise MaterialNotFoundException(material_id)

    precios = pricing_repo.get_historical_prices(material_id, desde or date(2000, 1, 1))
    if hasta:
        precios = [p for p in precios if p.fecha <= hasta]

    registros = [
        PrecioSerieInput(
            fecha=precio.fecha,
            precio_normalizado=precio.precio_normalizado,
            unidad_base=material.unidad_base,
            fuente=precio.fuente.nombre if precio.fuente else None,
            numero_comprobante=precio.numero_comprobante,
        )
        for precio in precios
    ]
    if agrupacion == "mensual":
        return construir_serie_mensual(registros)
    if agrupacion != "dia":
        raise HTTPException(status_code=422, detail="La agrupacion debe ser 'dia' o 'mensual'")
    return construir_serie_precios(registros)


@router.get("/materiales/{material_id}/forecast", response_model=ForecastResponseRead, response_model_exclude_none=True)
def obtener_forecast_material(
    material_id: int,
    horizonte_meses: int = 3,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
) -> ForecastResponseRead:
    if horizonte_meses < 1 or horizonte_meses > 12:
        raise HTTPException(status_code=422, detail="El horizonte_meses debe estar entre 1 y 12")

    material = material_repo.get_by_id(material_id)
    if material is None:
        raise MaterialNotFoundException(material_id)

    forecast_result = forecast_material(
        material,
        horizonte_meses,
        pricing_repo,
        usar_selector_modelo=USAR_SELECTOR_MODELO_FORECAST,
    )

    return ForecastResponseRead(
        material_id=material.id,
        material_nombre=material.nombre,
        unidad_base=material.unidad_base,
        horizonte_meses=horizonte_meses,
        modelo=forecast_result.modelo,
        supuesto_regresores=forecast_result.supuesto_regresores,
        ultima_fecha_observada=forecast_result.dataset[-1].ds,
        ultimo_precio_observado=Decimal(f"{forecast_result.dataset[-1].y:.2f}"),
        metricas=forecast_result.metricas,
        puntos=forecast_result.forecast,
        seleccion_modelo=forecast_result.seleccion_modelo,
    )


@router.post("/materiales/{material_id}/recomendacion-compra", response_model=PurchaseRecommendationRead)
def recomendar_momento_compra_material(
    material_id: int,
    payload: PurchaseRecommendationCreate,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
) -> PurchaseRecommendationRead:
    material = material_repo.get_by_id(material_id)
    if material is None:
        raise MaterialNotFoundException(material_id)

    result = recomendar_momento_compra(
        material,
        payload.horizonte_meses,
        payload.criticidad,
        payload.cantidad_objetivo,
        pricing_repo,
        usar_selector_modelo=USAR_SELECTOR_MODELO_FORECAST,
    )
    return PurchaseRecommendationRead(
        material_id=result.material_id,
        material_key=result.material_key,
        horizonte_meses=result.horizonte_meses,
        decision=result.decision,
        variacion_esperada_pct=result.variacion_esperada_pct,
        confiabilidad=result.confiabilidad,
        criticidad=result.criticidad,
        justificacion=result.justificacion,
        advertencias=list(result.advertencias),
    )


@router.post(
    "/materiales/{material_id}/comparacion-estrategias-compra",
    response_model=PurchaseStrategyComparisonRead,
)
def comparar_estrategias_compra_material(
    material_id: int,
    payload: PurchaseStrategyComparisonCreate,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
) -> PurchaseStrategyComparisonRead:
    material = material_repo.get_by_id(material_id)
    if material is None:
        raise MaterialNotFoundException(material_id)

    result = comparar_estrategias_compra(
        material,
        payload.horizonte_meses,
        payload.cantidad_objetivo,
        pricing_repo,
        porcentaje_compra_inmediata=payload.porcentaje_compra_inmediata,
        usar_selector_modelo=USAR_SELECTOR_MODELO_FORECAST,
    )

    return PurchaseStrategyComparisonRead(
        material_id=result.material_id,
        material_key=result.material_key,
        horizonte_meses=result.horizonte_meses,
        cantidad_objetivo=result.cantidad_objetivo,
        porcentaje_compra_inmediata=result.porcentaje_compra_inmediata,
        precio_actual=result.precio_actual,
        precio_proyectado_horizonte=result.precio_proyectado_horizonte,
        variacion_esperada_pct=result.variacion_esperada_pct,
        confiabilidad=result.confiabilidad,
        estrategias=[
            {
                "nombre": estrategia.nombre,
                "costo_estimado": estrategia.costo_estimado,
                "riesgo": estrategia.riesgo,
                "descripcion": estrategia.descripcion,
            }
            for estrategia in result.estrategias
        ],
        mejor_estrategia=result.mejor_estrategia,
        ahorro_estimado=result.ahorro_estimado,
        justificacion=result.justificacion,
        advertencias=list(result.advertencias),
    )


@router.post("/compras/optimizar-presupuesto", response_model=PurchaseOptimizationRead)
def optimizar_presupuesto_compra(
    payload: PurchaseOptimizationCreate,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
) -> PurchaseOptimizationRead:
    result = optimizar_compra_con_presupuesto(
        presupuesto_total=payload.presupuesto_total,
        horizonte_meses=payload.horizonte_meses,
        materiales=[
            PurchaseOptimizationInputItem(
                material_id=item.material_id,
                cantidad_objetivo=item.cantidad_objetivo,
                criticidad=item.criticidad,
            )
            for item in payload.materiales
        ],
        material_repo=material_repo,
        pricing_repo=pricing_repo,
        usar_selector_modelo=USAR_SELECTOR_MODELO_FORECAST,
    )

    return PurchaseOptimizationRead(
        presupuesto_total=result.presupuesto_total,
        presupuesto_utilizado=result.presupuesto_utilizado,
        presupuesto_restante=result.presupuesto_restante,
        horizonte_meses=result.horizonte_meses,
        estado_optimizacion=result.estado_optimizacion,
        items=[
            {
                "material_id": item.material_id,
                "material_key": item.material_key,
                "cantidad_objetivo": item.cantidad_objetivo,
                "cantidad_recomendada_comprar_ahora": item.cantidad_recomendada_comprar_ahora,
                "precio_actual": item.precio_actual,
                "precio_proyectado_horizonte": item.precio_proyectado_horizonte,
                "costo_compra_ahora": item.costo_compra_ahora,
                "ahorro_unitario_estimado": item.ahorro_unitario_estimado,
                "ahorro_total_estimado": item.ahorro_total_estimado,
                "criticidad": item.criticidad,
                "peso_criticidad": item.peso_criticidad,
                "confiabilidad": item.confiabilidad,
            }
            for item in result.items
        ],
        ahorro_total_estimado=result.ahorro_total_estimado,
        justificacion=result.justificacion,
        advertencias=list(result.advertencias),
    )


@router.post("/materiales/criticidad", response_model=MaterialCriticidadResponseRead)
def priorizar_materiales_por_criticidad(
    payload: MaterialCriticidadCreate,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    current_user: Usuario = Depends(get_current_user),
) -> MaterialCriticidadResponseRead:
    if payload.alpha == 0 and payload.beta == 0:
        raise HTTPException(status_code=422, detail="alpha y beta no pueden ser ambos cero")
    return priorizar_materiales_desde_forecast(payload, material_repo, pricing_repo)


@router.get("/admin/margenes", response_model=list[CommercialMarginRead])
def listar_margenes_comerciales(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> list[CommercialMarginRead]:
    margins = listar_margenes_comerciales_service(db)
    return [CommercialMarginRead.model_validate(margin) for margin in margins]


@router.post("/admin/margenes", response_model=CommercialMarginRead, status_code=status.HTTP_201_CREATED)
def crear_margen_comercial(
    payload: CommercialMarginCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> CommercialMarginRead:
    margin = crear_margen_comercial_service(db, **payload.model_dump())
    return CommercialMarginRead.model_validate(margin)


@router.patch("/admin/margenes/{margin_id}", response_model=CommercialMarginRead)
def actualizar_margen_comercial(
    margin_id: int,
    payload: CommercialMarginUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> CommercialMarginRead:
    margin = actualizar_margen_comercial_service(db, margin_id=margin_id, update_data=payload.model_dump(exclude_unset=True))
    return CommercialMarginRead.model_validate(margin)


@router.get("/materiales/{material_id}/precio-comercial", response_model=CommercialPriceRead)
def obtener_precio_comercial_material(
    material_id: int,
    presentacion_id: int | None = None,
    product_key: str | None = None,
    horizonte_meses: int = 3,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> CommercialPriceRead:
    if horizonte_meses < 1 or horizonte_meses > 12:
        raise HTTPException(status_code=422, detail="El horizonte_meses debe estar entre 1 y 12")

    material = material_repo.get_by_id(material_id)
    if material is None:
        raise MaterialNotFoundException(material_id)

    result = calcular_precio_comercial(
        material=material,
        pricing_repo=pricing_repo,
        db=db,
        horizonte_meses=horizonte_meses,
        presentation_id=presentacion_id,
        product_key=product_key,
        usar_selector_modelo=USAR_SELECTOR_MODELO_FORECAST,
    )
    return CommercialPriceRead(
        material_id=result.material_id,
        material_key=result.material_key,
        presentation_id=result.presentation_id,
        product_key=result.product_key,
        costo_base_actual=result.costo_base_actual,
        costo_base_proyectado=result.costo_base_proyectado,
        margen_ganancia_pct=result.margen_ganancia_pct,
        origen_margen=result.origen_margen,
        precio_final_actual=result.precio_final_actual,
        precio_final_proyectado=result.precio_final_proyectado,
        ganancia_unitaria_actual=result.ganancia_unitaria_actual,
        ganancia_unitaria_proyectada=result.ganancia_unitaria_proyectada,
        advertencias=list(result.advertencias),
    )


@router.post("/materiales/{material_id}/imputar-precios", response_model=PriceImputationResponse)
def imputar_precios_material(
    material_id: int,
    payload: PriceImputationRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> PriceImputationResponse:
    result = impute_monthly_prices(
        db,
        material_id=material_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        index_series_id=payload.index_series_id,
        source_name=payload.source_name,
        metodo_estimacion=payload.metodo_estimacion,
    )
    return PriceImputationResponse(
        material_id=result.material_id,
        source_name=result.source_name,
        series_id=result.series_id,
        metodo_estimacion=result.metodo_estimacion,
        inserted=result.inserted,
        updated=result.updated,
        skipped_real_months=result.skipped_real_months,
        generated_months=result.generated_months,
    )


@router.post("/precios-historicos", response_model=PrecioHistoricoRead, status_code=status.HTTP_201_CREATED)
def crear_precio_historico(
    payload: PrecioHistoricoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> PrecioHistorico:
    return crear_precio_historico_service(db, **payload.model_dump(), usuario_id=current_user.id)
