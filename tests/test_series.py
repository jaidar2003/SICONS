from datetime import date
from decimal import Decimal

import pytest

from app.modules.pricing.application.series import (
    PrecioSerieInput,
    calcular_variacion_entre_fechas,
    construir_serie_mensual,
    construir_serie_precios,
)


def test_construir_serie_precios_agrupa_por_fecha_y_calcula_equivalencias() -> None:
    serie = construir_serie_precios(
        [
            PrecioSerieInput(date(2026, 3, 3), Decimal("260.0000"), "kg", "Factura compra"),
            PrecioSerieInput(date(2026, 3, 3), Decimal("262.0000"), "kg", "Factura compra"),
            PrecioSerieInput(date(2026, 3, 25), Decimal("272.3980"), "kg", "Factura compra"),
        ]
    )

    assert len(serie) == 2
    assert serie[0].fecha == date(2026, 3, 3)
    assert serie[0].precio_promedio_normalizado == Decimal("261.0000")
    assert serie[0].precio_equivalente_25kg == Decimal("6525.0000")
    assert serie[0].precio_equivalente_50kg == Decimal("13050.0000")
    assert serie[0].cantidad_registros == 2
    assert serie[0].cantidad_facturas == 2
    assert serie[0].fuentes == ["Factura compra"]
    assert serie[0].variacion_porcentual_anterior is None
    assert serie[1].variacion_porcentual_anterior == Decimal("4.3670")


def test_construir_serie_mensual_promedia_y_detecta_anomalias_con_random_forest() -> None:
    serie = construir_serie_mensual(
        [
            PrecioSerieInput(date(2026, 1, 3), Decimal("100.0000"), "kg", "Factura compra", "A-0001"),
            PrecioSerieInput(date(2026, 1, 20), Decimal("120.0000"), "kg", "Factura compra", "A-0002"),
            PrecioSerieInput(date(2026, 2, 4), Decimal("112.0000"), "kg", "Lista proveedor", "A-0003"),
            PrecioSerieInput(date(2026, 3, 4), Decimal("114.0000"), "kg", "Lista proveedor", "A-0004"),
            PrecioSerieInput(date(2026, 4, 4), Decimal("116.0000"), "kg", "Lista proveedor", "A-0005"),
            PrecioSerieInput(date(2026, 5, 4), Decimal("118.0000"), "kg", "Lista proveedor", "A-0006"),
            PrecioSerieInput(date(2026, 6, 4), Decimal("120.0000"), "kg", "Lista proveedor", "A-0007"),
            PrecioSerieInput(date(2026, 7, 4), Decimal("170.0000"), "kg", "Lista proveedor", "A-0008"),
            PrecioSerieInput(date(2026, 8, 4), Decimal("124.0000"), "kg", "Lista proveedor", "A-0009"),
        ]
    )

    assert len(serie) == 8
    assert serie[0].fecha == date(2026, 1, 1)
    assert serie[0].precio_promedio_normalizado == Decimal("110.0000")
    assert serie[0].precio_equivalente_25kg == Decimal("2750.0000")
    assert serie[0].cantidad_registros == 2
    assert serie[0].cantidad_facturas == 2
    assert serie[0].es_anomalia is False
    assert serie[6].fecha == date(2026, 7, 1)
    assert serie[6].variacion_porcentual_anterior == Decimal("41.6667")
    assert serie[6].es_anomalia is True
    assert serie[6].severidad_anomalia in {"leve", "media", "alta"}
    assert serie[6].motivo_anomalia is not None
    assert "Random Forest" in serie[6].motivo_anomalia


def test_construir_serie_mensual_cuenta_facturas_distintas() -> None:
    serie = construir_serie_mensual(
        [
            PrecioSerieInput(date(2026, 1, 3), Decimal("100.0000"), "kg", "Factura compra", "A-0001"),
            PrecioSerieInput(date(2026, 1, 3), Decimal("102.0000"), "kg", "Factura compra", "A-0001"),
            PrecioSerieInput(date(2026, 1, 20), Decimal("104.0000"), "kg", "Factura compra", "A-0002"),
        ]
    )

    assert serie[0].cantidad_registros == 3
    assert serie[0].cantidad_facturas == 2


def test_construir_serie_mensual_no_calcula_bolsas_para_material_no_cemento() -> None:
    serie = construir_serie_mensual(
        [
            PrecioSerieInput(date(2026, 1, 3), Decimal("100.0000"), "kg", "Factura compra Proveedor", "A-0001"),
            PrecioSerieInput(date(2026, 1, 20), Decimal("120.0000"), "kg", "Factura compra Proveedor", "A-0002"),
        ]
    )

    assert serie[0].precio_equivalente_25kg is None
    assert serie[0].precio_equivalente_50kg is None


def test_calcular_variacion_entre_fechas_toma_ultimos_puntos_hasta_fechas_objetivo() -> None:
    registros = [
        PrecioSerieInput(date(2026, 1, 10), Decimal("100.0000"), "kg", "Factura compra"),
        PrecioSerieInput(date(2026, 2, 5), Decimal("110.0000"), "kg", "Factura compra"),
        PrecioSerieInput(date(2026, 3, 20), Decimal("121.0000"), "kg", "Factura compra"),
    ]

    result = calcular_variacion_entre_fechas(
        registros,
        fecha_desde=date(2026, 2, 1),
        fecha_hasta=date(2026, 3, 31),
    )

    assert result.fecha_desde == date(2026, 1, 10)
    assert result.fecha_hasta == date(2026, 3, 20)
    assert result.precio_desde == Decimal("100.0000")
    assert result.precio_hasta == Decimal("121.0000")
    assert result.variacion_porcentual == Decimal("21.0000")


def test_calcular_variacion_entre_fechas_falla_si_fechas_invalidas() -> None:
    registros = [PrecioSerieInput(date(2026, 1, 10), Decimal("100.0000"), "kg", "Factura compra")]

    with pytest.raises(ValueError, match="fecha_hasta debe ser posterior a fecha_desde"):
        calcular_variacion_entre_fechas(
            registros,
            fecha_desde=date(2026, 2, 1),
            fecha_hasta=date(2026, 2, 1),
        )
