from decimal import Decimal


def calcular_precio_normalizado(precio_original: Decimal, cantidad_base: Decimal) -> Decimal:
    if cantidad_base <= 0:
        raise ValueError("cantidad_base debe ser mayor a cero")
    return precio_original / cantidad_base
