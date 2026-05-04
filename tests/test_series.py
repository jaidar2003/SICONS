from datetime import date
from decimal import Decimal

from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios


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


def test_construir_serie_mensual_promedia_y_detecta_anomalias() -> None:
    serie = construir_serie_mensual(
        [
            PrecioSerieInput(date(2026, 1, 3), Decimal("100.0000"), "kg", "Factura compra", "A-0001"),
            PrecioSerieInput(date(2026, 1, 20), Decimal("120.0000"), "kg", "Factura compra", "A-0002"),
            PrecioSerieInput(date(2026, 2, 4), Decimal("132.0000"), "kg", "Lista proveedor", "A-0003"),
        ],
        umbral_anomalia=Decimal("8"),
    )

    assert len(serie) == 2
    assert serie[0].fecha == date(2026, 1, 1)
    assert serie[0].precio_promedio_normalizado == Decimal("110.0000")
    assert serie[0].precio_equivalente_25kg == Decimal("2750.0000")
    assert serie[0].cantidad_registros == 2
    assert serie[0].cantidad_facturas == 2
    assert serie[0].es_anomalia is False
    assert serie[1].fecha == date(2026, 2, 1)
    assert serie[1].variacion_porcentual_anterior == Decimal("20.0000")
    assert serie[1].es_anomalia is True
    assert serie[1].motivo_anomalia == "Variacion mensual de 20.0000%"


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
