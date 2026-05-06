from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import require_admin
from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.application.forecast_service import (
    forecast_material,
)
from app.modules.pricing.application.external_indices import list_external_indices, sync_external_index
from app.modules.pricing.application.imputation import impute_monthly_prices
from app.modules.pricing.application.purchase_recommendations import recomendar_momento_compra
from app.modules.pricing.application.purchase_strategies import comparar_estrategias_compra
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.modules.pricing.domain.exceptions import MaterialNotFoundException
from app.modules.pricing.application.priorities import priorizar_materiales_desde_forecast
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios
from app.modules.pricing.domain.rules import calcular_precio_normalizado
from app.modules.pricing.infrastructure.models import ExternalIndexValue, PrecioHistorico
from app.modules.pricing.interfaces.schemas import (
    ExternalIndexSyncRequest,
    ExternalIndexSyncResponse,
    ExternalIndexValueRead,
    ForecastResponseRead,
    MaterialCriticidadCreate,
    MaterialCriticidadRead,
    MaterialCriticidadResponseRead,
    PurchaseRecommendationCreate,
    PurchaseRecommendationRead,
    PurchaseStrategyComparisonCreate,
    PurchaseStrategyComparisonRead,
    PriceImputationRequest,
    PriceImputationResponse,
    PrecioHistoricoCreate,
    PrecioHistoricoRangoRead,
    PrecioHistoricoRead,
    PuntoSeriePrecioRead,
)
from app.shared.database.session import get_db


router = APIRouter(tags=["precios historicos"])
USAR_SELECTOR_MODELO_FORECAST = False

@router.get("/precios-historicos/rango", response_model=PrecioHistoricoRangoRead)
def obtener_rango_precios_historicos(db: Session = Depends(get_db)) -> PrecioHistoricoRangoRead:
    hoy = date.today()
    desde, hasta_real = db.execute(
        select(func.min(PrecioHistorico.fecha), func.max(PrecioHistorico.fecha))
    ).one()
    hasta = min(hasta_real, hoy) if hasta_real is not None else None
    return PrecioHistoricoRangoRead(
        desde=desde,
        hasta=hasta,
        hoy=hoy,
        tiene_fechas_futuras=hasta_real is not None and hasta_real > hoy,
        hasta_real=hasta_real,
    )


@router.get("/precios-historicos", response_model=list[PrecioHistoricoRead])
def listar_precios_historicos(
    material_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
) -> list[PrecioHistorico]:
    stmt = select(PrecioHistorico).order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    if material_id is not None:
        stmt = stmt.where(PrecioHistorico.material_id == material_id)
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)
    return list(db.scalars(stmt))


@router.get("/indices-externos", response_model=list[ExternalIndexValueRead])
def listar_indices_externos(
    series_id: str | None = None,
    source_name: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
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


@router.post("/materiales/criticidad", response_model=MaterialCriticidadResponseRead)
def priorizar_materiales_por_criticidad(
    payload: MaterialCriticidadCreate,
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
) -> MaterialCriticidadResponseRead:
    if payload.alpha == 0 and payload.beta == 0:
        raise HTTPException(status_code=422, detail="alpha y beta no pueden ser ambos cero")
    return priorizar_materiales_desde_forecast(payload, material_repo, pricing_repo)


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
    if payload.fecha > date.today():
        raise HTTPException(status_code=422, detail="La fecha no puede ser futura")

    material = db.get(Material, payload.material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    precio_normalizado = payload.precio_original
    if payload.presentacion_id is not None:
        presentacion = db.get(Presentacion, payload.presentacion_id)
        if presentacion is None:
            raise HTTPException(status_code=404, detail="Presentacion no encontrada")
        if presentacion.material_id != payload.material_id:
            raise HTTPException(status_code=422, detail="La presentacion no pertenece al material")
        precio_normalizado = calcular_precio_normalizado(payload.precio_original, Decimal(presentacion.cantidad_base))

    if payload.fuente_id is not None and db.get(Fuente, payload.fuente_id) is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    precio = PrecioHistorico(
        **payload.model_dump(),
        precio_normalizado=precio_normalizado,
    )
    db.add(precio)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El precio historico ya existe") from exc
    db.refresh(precio)
    return precio
