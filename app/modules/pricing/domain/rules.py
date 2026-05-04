from decimal import Decimal, ROUND_HALF_UP


def _quantize(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def calcular_precio_normalizado(precio_original: Decimal, cantidad_base: Decimal) -> Decimal:
    if cantidad_base <= 0:
        raise ValueError("cantidad_base debe ser mayor a cero")
    return precio_original / cantidad_base


def calcular_impacto_absoluto(
    precio_actual_normalizado: Decimal,
    precio_proyectado_normalizado: Decimal,
    cantidad_requerida: Decimal,
) -> Decimal:
    if cantidad_requerida < 0:
        raise ValueError("cantidad_requerida no puede ser negativa")
    return _quantize((precio_proyectado_normalizado - precio_actual_normalizado) * cantidad_requerida)


def calcular_variacion_esperada_porcentual(
    precio_actual_normalizado: Decimal,
    precio_proyectado_normalizado: Decimal,
) -> Decimal:
    if precio_actual_normalizado <= 0:
        return Decimal("0")
    return _quantize(((precio_proyectado_normalizado - precio_actual_normalizado) / precio_actual_normalizado) * Decimal("100"))


def normalizar_valores(valores: list[Decimal]) -> list[Decimal]:
    if not valores:
        return []

    maximo = max((abs(valor) for valor in valores), default=Decimal("0"))
    if maximo == 0:
        return [Decimal("0") for _ in valores]

    return [_quantize(abs(valor) / maximo) for valor in valores]


def calcular_puntaje_criticidad(
    variacion_normalizada: Decimal,
    impacto_normalizado: Decimal,
    alpha: Decimal,
    beta: Decimal,
) -> Decimal:
    if alpha < 0 or beta < 0:
        raise ValueError("alpha y beta deben ser no negativos")

    total_pesos = alpha + beta
    if total_pesos == 0:
        raise ValueError("alpha y beta no pueden ser ambos cero")

    puntaje = ((alpha * variacion_normalizada) + (beta * impacto_normalizado)) / total_pesos
    return _quantize(puntaje)


def etiquetar_criticidad(puntaje: Decimal) -> str:
    if puntaje >= Decimal("0.67"):
        return "alta"
    if puntaje >= Decimal("0.34"):
        return "media"
    return "baja"


def explicar_priorizacion(
    variacion_normalizada: Decimal,
    impacto_normalizado: Decimal,
    variacion_esperada_porcentual: Decimal,
    impacto_absoluto: Decimal,
) -> str:
    if variacion_esperada_porcentual <= 0 and impacto_absoluto <= 0:
        return "Sin aumento proyectado relevante en el horizonte analizado."

    if variacion_normalizada == impacto_normalizado:
        return "Priorizado por combinacion equilibrada de aumento esperado e impacto presupuestario."

    if impacto_normalizado > variacion_normalizada:
        return "Priorizado principalmente por su mayor impacto presupuestario esperado."

    return "Priorizado principalmente por su mayor variacion esperada."
