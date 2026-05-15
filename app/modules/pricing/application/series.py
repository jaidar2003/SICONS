from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from statistics import median


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


@dataclass(frozen=True)
class VariacionEntreFechas:
    fecha_desde: date
    fecha_hasta: date
    precio_desde: Decimal
    precio_hasta: Decimal
    variacion_porcentual: Decimal


def _quantize(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _contar_facturas(registros: list[PrecioSerieInput]) -> int:
    comprobantes = {registro.numero_comprobante for registro in registros if registro.numero_comprobante}
    return len(comprobantes) if comprobantes else len(registros)


def _usa_equivalencias_bolsa(unidad_base: str, fuentes: list[str]) -> bool:
    return unidad_base == "kg" and "Factura compra" in fuentes


def _ultimo_precio_hasta_fecha(registros: list[PrecioSerieInput], fecha_objetivo: date) -> tuple[date, Decimal] | None:
    candidatos = [registro for registro in registros if registro.fecha <= fecha_objetivo]
    if not candidatos:
        return None
    ultimo = max(candidatos, key=lambda registro: registro.fecha)
    return ultimo.fecha, ultimo.precio_normalizado


def calcular_variacion_entre_fechas(
    registros: list[PrecioSerieInput],
    fecha_desde: date,
    fecha_hasta: date,
) -> VariacionEntreFechas:
    if fecha_hasta <= fecha_desde:
        raise ValueError("fecha_hasta debe ser posterior a fecha_desde")

    punto_desde = _ultimo_precio_hasta_fecha(registros, fecha_desde)
    if punto_desde is None:
        raise ValueError("No hay precio historico para fecha_desde")

    punto_hasta = _ultimo_precio_hasta_fecha(registros, fecha_hasta)
    if punto_hasta is None:
        raise ValueError("No hay precio historico para fecha_hasta")

    fecha_real_desde, precio_desde = punto_desde
    fecha_real_hasta, precio_hasta = punto_hasta
    if precio_desde == 0:
        raise ValueError("No se puede calcular variacion con precio_desde en cero")

    variacion = _quantize(((precio_hasta - precio_desde) / precio_desde) * Decimal("100"))
    return VariacionEntreFechas(
        fecha_desde=fecha_real_desde,
        fecha_hasta=fecha_real_hasta,
        precio_desde=_quantize(precio_desde),
        precio_hasta=_quantize(precio_hasta),
        variacion_porcentual=variacion,
    )


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


def _features_anomalia_mensual(puntos: list[PuntoSeriePrecio], index: int) -> list[float]:
    punto = puntos[index]
    anterior = puntos[index - 1]
    precios_previos = [float(item.precio_promedio_normalizado) for item in puntos[max(0, index - 3) : index]]
    variacion_anterior = float(anterior.variacion_porcentual_anterior or Decimal("0"))
    return [
        float(index),
        float(punto.fecha.month),
        float(anterior.precio_promedio_normalizado),
        variacion_anterior,
        sum(precios_previos) / len(precios_previos),
        float(punto.cantidad_registros),
    ]


def _detectar_anomalias_random_forest(puntos: list[PuntoSeriePrecio]) -> dict[date, str]:
    if len(puntos) < 6:
        return {}

    from sklearn.ensemble import RandomForestRegressor

    trainable_indexes = [index for index in range(1, len(puntos))]
    x_train = [_features_anomalia_mensual(puntos, index) for index in trainable_indexes]
    y_train = [float(puntos[index].precio_promedio_normalizado) for index in trainable_indexes]
    if len(x_train) < 5:
        return {}

    model = RandomForestRegressor(
        n_estimators=120,
        max_depth=4,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_train)
    residuals_pct = [
        abs((actual - predicted) / predicted) * 100 if predicted else 0
        for actual, predicted in zip(y_train, predictions)
    ]
    if not residuals_pct:
        return {}

    sorted_residuals = sorted(residuals_pct)
    mitad = len(sorted_residuals) // 2
    lower_half = sorted_residuals[:mitad]
    upper_half = sorted_residuals[mitad + (0 if len(sorted_residuals) % 2 == 0 else 1) :]
    q1 = median(lower_half) if lower_half else sorted_residuals[0]
    q3 = median(upper_half) if upper_half else sorted_residuals[-1]
    iqr = q3 - q1
    residual_limit = Decimal(f"{q3:.6f}") + (Decimal("1.5") * Decimal(f"{iqr:.6f}"))

    anomalies: dict[date, str] = {}
    for index, residual_pct, predicted in zip(trainable_indexes, residuals_pct, predictions):
        if Decimal(f"{residual_pct:.6f}") <= residual_limit:
            continue

        variacion = puntos[index].variacion_porcentual_anterior
        if variacion is None:
            continue

        anomalies[puntos[index].fecha] = (
            "Anomalia detectada por Random Forest: "
            f"precio esperado {Decimal(f'{predicted:.4f}').quantize(Decimal('0.0001'))}, "
            f"residuo {Decimal(f'{residual_pct:.4f}').quantize(Decimal('0.0001'))}% "
            f"y variacion mensual {variacion}%"
        )

    return anomalies


def construir_serie_mensual(registros: list[PrecioSerieInput]) -> list[PuntoSeriePrecio]:
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
        if precio_anterior is not None and precio_anterior != 0:
            variacion = _quantize(((promedio - precio_anterior) / precio_anterior) * Decimal("100"))

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
            )
        )
        precio_anterior = promedio

    anomalies = _detectar_anomalias_random_forest(puntos)
    if anomalies:
        puntos = [
            PuntoSeriePrecio(
                fecha=punto.fecha,
                precio_promedio_normalizado=punto.precio_promedio_normalizado,
                unidad_base=punto.unidad_base,
                precio_equivalente_25kg=punto.precio_equivalente_25kg,
                precio_equivalente_50kg=punto.precio_equivalente_50kg,
                cantidad_registros=punto.cantidad_registros,
                cantidad_facturas=punto.cantidad_facturas,
                fuentes=punto.fuentes,
                variacion_porcentual_anterior=punto.variacion_porcentual_anterior,
                es_anomalia=punto.fecha in anomalies,
                motivo_anomalia=anomalies.get(punto.fecha),
            )
            for punto in puntos
        ]

    return puntos
