from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class PrecioSerieInput:
    fecha: date
    precio_normalizado: Decimal
    unidad_base: str
    fuente: str | None = None
    numero_comprobante: str | None = None


@dataclass(frozen=True)
class PuntoSeriePrecio:
    fecha: date
    precio_promedio_normalizado: Decimal
    unidad_base: str
    precio_equivalente_25kg: Decimal | None
    precio_equivalente_50kg: Decimal | None
    cantidad_registros: int
    cantidad_facturas: int
    fuentes: list[str]
    variacion_porcentual_anterior: Decimal | None
    es_anomalia: bool = False
    motivo_anomalia: str | None = None


def _quantize(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _contar_facturas(registros: list[PrecioSerieInput]) -> int:
    comprobantes = {registro.numero_comprobante for registro in registros if registro.numero_comprobante}
    return len(comprobantes) if comprobantes else len(registros)


def _usa_equivalencias_bolsa(unidad_base: str, fuentes: list[str]) -> bool:
    return unidad_base == "kg" and "Factura compra" in fuentes


def construir_serie_precios(registros: list[PrecioSerieInput]) -> list[PuntoSeriePrecio]:
    grupos: dict[date, list[PrecioSerieInput]] = defaultdict(list)
    for registro in registros:
        grupos[registro.fecha].append(registro)

    puntos: list[PuntoSeriePrecio] = []
    precio_anterior: Decimal | None = None

    for fecha_punto in sorted(grupos):
        registros_fecha = grupos[fecha_punto]
        total = sum((registro.precio_normalizado for registro in registros_fecha), Decimal("0"))
        promedio = _quantize(total / Decimal(len(registros_fecha)))
        unidad_base = registros_fecha[0].unidad_base
        fuentes = sorted({registro.fuente for registro in registros_fecha if registro.fuente})
        usa_equivalencias = _usa_equivalencias_bolsa(unidad_base, fuentes)

        variacion = None
        if precio_anterior is not None and precio_anterior != 0:
            variacion = _quantize(((promedio - precio_anterior) / precio_anterior) * Decimal("100"))

        puntos.append(
            PuntoSeriePrecio(
                fecha=fecha_punto,
                precio_promedio_normalizado=promedio,
                unidad_base=unidad_base,
                precio_equivalente_25kg=_quantize(promedio * Decimal("25")) if usa_equivalencias else None,
                precio_equivalente_50kg=_quantize(promedio * Decimal("50")) if usa_equivalencias else None,
                cantidad_registros=len(registros_fecha),
                cantidad_facturas=_contar_facturas(registros_fecha),
                fuentes=fuentes,
                variacion_porcentual_anterior=variacion,
            )
        )
        precio_anterior = promedio

    return puntos


def construir_serie_mensual(
    registros: list[PrecioSerieInput],
    umbral_anomalia: Decimal = Decimal("8"),
) -> list[PuntoSeriePrecio]:
    grupos: dict[date, list[PrecioSerieInput]] = defaultdict(list)
    for registro in registros:
        mes = date(registro.fecha.year, registro.fecha.month, 1)
        grupos[mes].append(registro)

    puntos: list[PuntoSeriePrecio] = []
    precio_anterior: Decimal | None = None

    for mes in sorted(grupos):
        registros_mes = grupos[mes]
        total = sum((registro.precio_normalizado for registro in registros_mes), Decimal("0"))
        promedio = _quantize(total / Decimal(len(registros_mes)))
        unidad_base = registros_mes[0].unidad_base
        fuentes = sorted({registro.fuente for registro in registros_mes if registro.fuente})
        usa_equivalencias = _usa_equivalencias_bolsa(unidad_base, fuentes)

        variacion = None
        es_anomalia = False
        motivo_anomalia = None
        if precio_anterior is not None and precio_anterior != 0:
            variacion = _quantize(((promedio - precio_anterior) / precio_anterior) * Decimal("100"))
            es_anomalia = abs(variacion) >= umbral_anomalia
            if es_anomalia:
                motivo_anomalia = f"Variacion mensual de {variacion}%"

        puntos.append(
            PuntoSeriePrecio(
                fecha=mes,
                precio_promedio_normalizado=promedio,
                unidad_base=unidad_base,
                precio_equivalente_25kg=_quantize(promedio * Decimal("25")) if usa_equivalencias else None,
                precio_equivalente_50kg=_quantize(promedio * Decimal("50")) if usa_equivalencias else None,
                cantidad_registros=len(registros_mes),
                cantidad_facturas=_contar_facturas(registros_mes),
                fuentes=fuentes,
                variacion_porcentual_anterior=variacion,
                es_anomalia=es_anomalia,
                motivo_anomalia=motivo_anomalia,
            )
        )
        precio_anterior = promedio

    return puntos
