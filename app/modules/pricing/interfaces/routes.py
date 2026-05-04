from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import require_admin
from app.modules.pricing.application.forecast_service import (
    FORECAST_MODEL_NAME,
    FORECAST_REGRESSOR_NOTE,
    forecast_material,
)
from app.modules.pricing.application.priorities import priorizar_materiales_desde_forecast
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios
from app.modules.pricing.domain.rules import calcular_precio_normalizado
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.modules.pricing.interfaces.schemas import (
    ForecastResponseRead,
    MaterialCriticidadCreate,
    MaterialCriticidadRead,
    MaterialCriticidadResponseRead,
    PrecioHistoricoCreate,
    PrecioHistoricoRangoRead,
    PrecioHistoricoRead,
    PuntoSeriePrecioRead,
)
from app.shared.database.session import get_db


router = APIRouter(tags=["precios historicos"])

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


@router.get("/materiales/{material_id}/precios", response_model=list[PrecioHistoricoRead])
def listar_precios_por_material(
    material_id: int,
    db: Session = Depends(get_db),
) -> list[PrecioHistorico]:
    if db.get(Material, material_id) is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    stmt = (
        select(PrecioHistorico)
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    )
    return list(db.scalars(stmt))


@router.get("/materiales/{material_id}/serie-precios", response_model=list[PuntoSeriePrecioRead])
def obtener_serie_precios_material(
    material_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    agrupacion: str = "dia",
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    stmt = (
        select(PrecioHistorico)
        .options(joinedload(PrecioHistorico.fuente))
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
    )
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)

    registros = [
        PrecioSerieInput(
            fecha=precio.fecha,
            precio_normalizado=precio.precio_normalizado,
            unidad_base=material.unidad_base,
            fuente=precio.fuente.nombre if precio.fuente else None,
            numero_comprobante=precio.numero_comprobante,
        )
        for precio in db.scalars(stmt)
    ]
    if agrupacion == "mensual":
        return construir_serie_mensual(registros)
    if agrupacion != "dia":
        raise HTTPException(status_code=422, detail="La agrupacion debe ser 'dia' o 'mensual'")
    return construir_serie_precios(registros)


@router.get("/materiales/{material_id}/forecast", response_model=ForecastResponseRead)
def obtener_forecast_material(
    material_id: int,
    horizonte_meses: int = 3,
    db: Session = Depends(get_db),
) -> ForecastResponseRead:
    if horizonte_meses < 1 or horizonte_meses > 12:
        raise HTTPException(status_code=422, detail="El horizonte_meses debe estar entre 1 y 12")

    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    forecast_result = forecast_material(material, horizonte_meses, db)

    return ForecastResponseRead(
        material_id=material.id,
        material_nombre=material.nombre,
        unidad_base=material.unidad_base,
        horizonte_meses=horizonte_meses,
        modelo=FORECAST_MODEL_NAME,
        supuesto_regresores=FORECAST_REGRESSOR_NOTE,
        ultima_fecha_observada=forecast_result.dataset[-1].ds,
        ultimo_precio_observado=Decimal(f"{forecast_result.dataset[-1].y:.2f}"),
        metricas=forecast_result.metricas,
        puntos=forecast_result.forecast,
    )


@router.post("/materiales/criticidad", response_model=MaterialCriticidadResponseRead)
def priorizar_materiales_por_criticidad(
    payload: MaterialCriticidadCreate,
    db: Session = Depends(get_db),
) -> MaterialCriticidadResponseRead:
    if payload.alpha == 0 and payload.beta == 0:
        raise HTTPException(status_code=422, detail="alpha y beta no pueden ser ambos cero")
    return priorizar_materiales_desde_forecast(payload, db)


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
