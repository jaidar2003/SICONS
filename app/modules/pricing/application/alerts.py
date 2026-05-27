import json
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.domain.rules import calcular_variacion_esperada_porcentual
from app.modules.pricing.infrastructure.models import Alerta, PrecioHistorico


def generar_alertas_proactivas(db: Session, pricing_repo) -> int:
    """
    Motor de generacion de alertas proactivas.
    Analiza desvios de precio, oportunidades de compra y deterioro de confianza.
    """
    materiales = db.query(Material).filter(Material.activo.is_(True)).all()
    count = 0

    for material in materiales:
        # 1. Alerta de Oportunidad de Compra
        # Horizonte de 3 meses para la alerta base
        forecast = forecast_material(material, 3, pricing_repo, usar_selector_modelo=True)
        if forecast and forecast.forecast:
            ultimo_precio = Decimal(f"{forecast.dataset[-1].y:.2f}")
            punto_futuro = forecast.forecast[-1]
            variacion = calcular_variacion_esperada_porcentual(ultimo_precio, punto_futuro.precio_proyectado)

            # Si la suba es > 10%, es una oportunidad clara de stockeo
            if variacion >= 10:
                _crear_alerta_si_no_existe(
                    db,
                    material_id=material.id,
                    tipo="OPORTUNIDAD_COMPRA",
                    prioridad="ALTA",
                    titulo=f"Oportunidad de stockeo: {material.nombre}",
                    mensaje=(
                        f"Se proyecta una suba del {variacion}% en los proximos 3 meses. "
                        f"El precio podria pasar de ARS {ultimo_precio} a ARS {punto_futuro.precio_proyectado}."
                    ),
                    data_context={"variacion": str(variacion), "precio_actual": str(ultimo_precio), "precio_futuro": str(punto_futuro.precio_proyectado)}
                )
                count += 1

            # 2. Alerta de Deterioro de Confianza
            mape = forecast.metricas.mape
            if mape > 15:
                _crear_alerta_si_no_existe(
                    db,
                    material_id=material.id,
                    tipo="DETERIORO_CONFIANZA",
                    prioridad="MEDIA",
                    titulo=f"Baja confiabilidad en forecast: {material.nombre}",
                    mensaje=(
                        f"El error del modelo (MAPE) ha subido a {mape}%. "
                        "Las proyecciones para este material podrian ser menos precisas de lo habitual."
                    ),
                    data_context={"mape": str(mape)}
                )
                count += 1

            # 3. Alerta de Desvio de Precio (Real vs Proyectado)
            # Buscamos el ultimo precio real cargado este mes
            hoy = date.today()
            ultimo_real = (
                db.query(PrecioHistorico)
                .filter(PrecioHistorico.material_id == material.id)
                .filter(PrecioHistorico.origen_dato == "REAL")
                .order_by(PrecioHistorico.fecha.desc())
                .first()
            )

            if ultimo_real and ultimo_real.fecha.month == hoy.month:
                # Comparamos con el pesimista del forecast (si existiera un punto para este mes)
                # En una version mas compleja, comparariamos con el forecast generado el mes pasado.
                # Por ahora, si el precio actual es > pesimista proyectado, alertamos.
                if punto_futuro.precio_pesimista and ultimo_real.precio_normalizado > punto_futuro.precio_pesimista:
                     _crear_alerta_si_no_existe(
                        db,
                        material_id=material.id,
                        tipo="DESVIO_PRECIO",
                        prioridad="ALTA",
                        titulo=f"Desvio critico de precio: {material.nombre}",
                        mensaje=(
                            f"El precio real detectado (ARS {ultimo_real.precio_normalizado}) "
                            f"ha superado el escenario pesimista (ARS {punto_futuro.precio_pesimista})."
                        ),
                        data_context={"precio_real": str(ultimo_real.precio_normalizado), "limite_pesimista": str(punto_futuro.precio_pesimista)}
                    )
                     count += 1

    db.commit()
    return count


def _crear_alerta_si_no_existe(db: Session, material_id: int, tipo: str, prioridad: str, titulo: str, mensaje: str, data_context: dict):
    # Evitamos duplicar alertas identicas para el mismo material y tipo en las ultimas 24hs
    from datetime import datetime, timedelta
    hace_24h = datetime.now() - timedelta(days=1)
    reciente = (
        db.query(Alerta)
        .filter(Alerta.material_id == material_id)
        .filter(Alerta.tipo == tipo)
        .filter(Alerta.created_at >= hace_24h)
        .first()
    )

    if not reciente:
        nueva = Alerta(
            material_id=material_id,
            tipo=tipo,
            prioridad=prioridad,
            titulo=titulo,
            mensaje=mensaje,
            data_context=json.dumps(data_context),
            leida=False
        )
        db.add(nueva)
