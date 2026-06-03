from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.application import purchase_recommendations as purchase_recommendations_module
from app.modules.pricing.application.purchase_recommendations import (
    CONFIANZA_ALTA,
    CONFIANZA_BAJA,
    CONFIANZA_MEDIA,
    DECISION_COMPRAR_AHORA,
    DECISION_ESPERAR,
    DECISION_MONITOREAR,
    evaluar_recomendacion_compra,
    recomendar_momento_compra,
)
from app.modules.pricing.application.series import PuntoSeriePrecio
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead, ForecastSelectionRead


def _fake_forecast_result(
    *,
    actual: str = "100.00",
    proyectado: str = "108.40",
    confiabilidad: str = CONFIANZA_ALTA,
    no_calibrado: bool = False,
    seleccion_modelo: ForecastSelectionRead | None = None,
    serie_mensual: list[PuntoSeriePrecio] | None = None,
):
    if seleccion_modelo is None and confiabilidad != "derivada":
        seleccion_modelo = ForecastSelectionRead(
            material_key="cemento-portland",
            modelo_resuelto="prophet_ipim_nivel_general",
            regresores_resueltos=["ipim_nivel_general"],
            mape_referencia=Decimal("4.98"),
            mae_referencia=Decimal("6.76"),
            folds=9,
            confiabilidad=confiabilidad,
            origen_decision="material_horizonte",
            justificacion="Configuracion recomendada.",
            no_calibrado=no_calibrado,
        )

    return SimpleNamespace(
        dataset=[SimpleNamespace(ds=date(2024, 1, 1), y=float(actual))],
        forecast=[ForecastPuntoRead(fecha=date(2024, 2, 1), precio_proyectado=Decimal(proyectado))],
        metricas=ForecastMetricasRead(
            folds=9,
            mae=Decimal("6.76"),
            mape=Decimal("4.98"),
            efectividad_informal=Decimal("95.02"),
        ),
        seleccion_modelo=seleccion_modelo,
        serie_mensual=serie_mensual,
    )


def test_alza_fuerte_con_criticidad_alta_y_confiabilidad_alta_compra_ahora() -> None:
    result = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("8.4000"),
        confiabilidad=CONFIANZA_ALTA,
        criticidad="alta",
        no_calibrado=False,
    )

    assert result.decision == DECISION_COMPRAR_AHORA
    assert "variacion esperada" in result.justificacion.lower()
    assert "criticidad" in result.justificacion.lower()
    assert "confiabilidad" in result.justificacion.lower()


def test_baja_fuerte_con_criticidad_baja_esperar() -> None:
    result = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("-8.0000"),
        confiabilidad=CONFIANZA_MEDIA,
        criticidad="baja",
        no_calibrado=False,
    )

    assert result.decision == DECISION_ESPERAR


def test_variacion_neutra_monitorear() -> None:
    result = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("0.2000"),
        confiabilidad=CONFIANZA_MEDIA,
        criticidad="media",
        no_calibrado=False,
    )

    assert result.decision == DECISION_MONITOREAR


def test_no_calibrado_monitorear() -> None:
    result = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("8.4000"),
        confiabilidad=CONFIANZA_ALTA,
        criticidad="alta",
        no_calibrado=True,
    )

    assert result.decision == DECISION_MONITOREAR
    assert "modelo no esta calibrado" in result.justificacion
    assert "confiabilidad es alta o" not in result.justificacion


def test_confiabilidad_baja_monitorear() -> None:
    result = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("8.4000"),
        confiabilidad=CONFIANZA_BAJA,
        criticidad="alta",
        no_calibrado=False,
    )

    assert result.decision == DECISION_MONITOREAR
    assert "confiabilidad del forecast es baja" in result.justificacion


def test_criticidad_alta_evita_esperar_salvo_baja_fuerte() -> None:
    moderada = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("-3.0000"),
        confiabilidad=CONFIANZA_ALTA,
        criticidad="alta",
        no_calibrado=False,
    )
    fuerte = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("-8.0000"),
        confiabilidad=CONFIANZA_ALTA,
        criticidad="alta",
        no_calibrado=False,
    )

    assert moderada.decision == DECISION_MONITOREAR
    assert fuerte.decision == DECISION_ESPERAR


def test_justificacion_menciona_variacion_criticidad_y_confiabilidad() -> None:
    result = evaluar_recomendacion_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        variacion_esperada_pct=Decimal("8.4000"),
        confiabilidad=CONFIANZA_ALTA,
        criticidad="alta",
        no_calibrado=False,
    )

    texto = result.justificacion.lower()
    assert "variacion" in texto
    assert "criticidad" in texto
    assert "confiabilidad" in texto


def test_recomendar_momento_compra_deriva_material_key_y_retorna_contrato(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result(actual="100.00", proyectado="108.40")

    monkeypatch.setattr(
        purchase_recommendations_module,
        "forecast_material",
        lambda *args, **kwargs: fake_forecast_result,
    )

    result = recomendar_momento_compra(
        material,
        3,
        "alta",
        Decimal("100"),
        pricing_repo=object(),
        usar_selector_modelo=False,
    )

    assert result.material_id == 1
    assert result.material_key == derive_material_key("Cemento Portland")
    assert result.decision == DECISION_COMPRAR_AHORA
    assert result.variacion_esperada_pct == Decimal("8.4000")
    assert result.impacto_economico_estimado == Decimal("840.00")
    assert result.mape == Decimal("4.98")
    assert result.umbral_decision_pct == Decimal("5")
    assert result.supera_umbral_decision is True


def test_recomendar_momento_compra_monitorea_si_no_hay_forecast(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    def raise_http_exception(*_args, **_kwargs):
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="No hay datos suficientes")

    monkeypatch.setattr(
        purchase_recommendations_module,
        "forecast_material",
        raise_http_exception,
    )

    result = recomendar_momento_compra(
        material,
        3,
        "alta",
        Decimal("100"),
        pricing_repo=object(),
        usar_selector_modelo=False,
    )

    assert result.decision == DECISION_MONITOREAR
    assert result.variacion_esperada_pct is None
    assert result.advertencias


def test_recomendar_momento_compra_monitorea_si_las_anomalias_son_altas(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result(
        actual="100.00",
        proyectado="108.40",
        serie_mensual=[
            PuntoSeriePrecio(
                fecha=date(2024, 1, 1),
                precio_promedio_normalizado=Decimal("100.0000"),
                unidad_base="kg",
                precio_equivalente_25kg=Decimal("2500.0000"),
                precio_equivalente_50kg=Decimal("5000.0000"),
                cantidad_registros=1,
                cantidad_facturas=1,
                fuentes=["Factura compra"],
                variacion_porcentual_anterior=None,
            ),
            PuntoSeriePrecio(
                fecha=date(2024, 2, 1),
                precio_promedio_normalizado=Decimal("180.0000"),
                unidad_base="kg",
                precio_equivalente_25kg=Decimal("4500.0000"),
                precio_equivalente_50kg=Decimal("9000.0000"),
                cantidad_registros=1,
                cantidad_facturas=1,
                fuentes=["Factura compra"],
                variacion_porcentual_anterior=Decimal("80.0000"),
                es_anomalia=True,
                severidad_anomalia="alta",
                motivo_anomalia="Anomalia detectada por Random Forest: precio esperado 100.0000, residuo 80.0000% y variacion mensual 80.0000%",
            ),
        ],
    )

    monkeypatch.setattr(
        purchase_recommendations_module,
        "forecast_material",
        lambda *args, **kwargs: fake_forecast_result,
    )

    result = recomendar_momento_compra(
        material,
        3,
        "alta",
        Decimal("100"),
        pricing_repo=object(),
        usar_selector_modelo=False,
    )

    assert result.decision == DECISION_MONITOREAR
    assert any("anomali" in advertencia.lower() for advertencia in result.advertencias)


def test_endpoint_responde_con_contrato_esperado(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result(actual="100.00", proyectado="108.40")
    monkeypatch.setattr(purchase_recommendations_module, "forecast_material", lambda *args, **kwargs: fake_forecast_result)

    class FakeMaterialRepo:
        def get_by_id(self, material_id: int):
            return material if material_id == 1 else None

    class FakePricingRepo:
        pass

    app.dependency_overrides[get_material_repository] = lambda: FakeMaterialRepo()
    app.dependency_overrides[get_pricing_repository] = lambda: FakePricingRepo()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")

    try:
        client = TestClient(app)
        response = client.post(
            "/materiales/1/recomendacion-compra",
            json={"horizonte_meses": 3, "criticidad": "alta", "cantidad_objetivo": 100},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["material_id"] == 1
    assert body["material_key"] == "cemento-portland"
    assert body["decision"] == DECISION_COMPRAR_AHORA
    assert body["criticidad"] == "alta"
    assert body["horizonte_meses"] == 3
    assert body["variacion_esperada_pct"] is not None
    assert body["precio_actual"] == "100.00"
    assert body["precio_proyectado_horizonte"] == "108.40"
    assert body["impacto_economico_estimado"] == "840.00"
    assert body["mape"] == "4.98"
    assert body["umbral_decision_pct"] == "5"
    assert body["supera_umbral_decision"] is True
    assert body["advertencias"] == []


def test_resolver_confiabilidad_derivada() -> None:
    from app.modules.pricing.application.purchase_recommendations import _resolver_confiabilidad
    
    # MAPE <= 5 -> alta
    res = SimpleNamespace(metricas=SimpleNamespace(mape=Decimal("4")), seleccion_modelo=None)
    assert _resolver_confiabilidad(res) == "alta"
    
    # MAPE <= 8 -> media
    res = SimpleNamespace(metricas=SimpleNamespace(mape=Decimal("7")), seleccion_modelo=None)
    assert _resolver_confiabilidad(res) == "media"
    
    # MAPE <= 12 -> media-baja
    res = SimpleNamespace(metricas=SimpleNamespace(mape=Decimal("10")), seleccion_modelo=None)
    assert _resolver_confiabilidad(res) == "media-baja"
    
    # MAPE > 12 -> baja
    res = SimpleNamespace(metricas=SimpleNamespace(mape=Decimal("15")), seleccion_modelo=None)
    assert _resolver_confiabilidad(res) == "baja"
    
    # MAPE is None -> no_disponible
    res = SimpleNamespace(metricas=SimpleNamespace(mape=None), seleccion_modelo=None)
    assert _resolver_confiabilidad(res) == "no_disponible"


def test_resolver_umbral_decision() -> None:
    from app.modules.pricing.application.purchase_recommendations import _resolver_umbral_decision
    assert _resolver_umbral_decision(None) == Decimal("5")
    assert _resolver_umbral_decision(Decimal("3")) == Decimal("5")
    assert _resolver_umbral_decision(Decimal("10")) == Decimal("10")


def test_calcular_impacto_economico_missing() -> None:
    from app.modules.pricing.application.purchase_recommendations import _calcular_impacto_economico
    assert _calcular_impacto_economico(precio_actual=None, precio_proyectado_horizonte=Decimal("10"), cantidad_objetivo=Decimal("1")) is None
    assert _calcular_impacto_economico(precio_actual=Decimal("10"), precio_proyectado_horizonte=None, cantidad_objetivo=Decimal("1")) is None
    assert _calcular_impacto_economico(precio_actual=Decimal("10"), precio_proyectado_horizonte=Decimal("10"), cantidad_objetivo=None) is None


def test_evaluar_recomendacion_compra_confianza_media_baja() -> None:
    # Confianza media-baja and alza fuerte -> COMPRAR_AHORA
    result = evaluar_recomendacion_compra(
        material_id=1, material_key="k", horizonte_meses=3, cantidad_objetivo=Decimal("1"),
        variacion_esperada_pct=Decimal("15"), confiabilidad="media-baja", criticidad="alta", no_calibrado=False
    )
    assert result.decision == DECISION_COMPRAR_AHORA
    
    # Confianza media-baja and alza moderada -> MONITOREAR
    result = evaluar_recomendacion_compra(
        material_id=1, material_key="k", horizonte_meses=3, cantidad_objetivo=Decimal("1"),
        variacion_esperada_pct=Decimal("4"), confiabilidad="media-baja", criticidad="alta", no_calibrado=False
    )
    assert result.decision == DECISION_MONITOREAR


def test_recomendar_momento_compra_empty_forecast(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    monkeypatch.setattr(
        purchase_recommendations_module,
        "forecast_material",
        lambda *args, **kwargs: SimpleNamespace(forecast=[], dataset=[])
    )
    result = recomendar_momento_compra(material, 3, "alta", Decimal("100"), pricing_repo=object())
    assert result.decision == DECISION_MONITOREAR
    assert "no devolvio puntos proyectados" in result.advertencias[0]


def test_recomendar_momento_compra_empty_dataset(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    monkeypatch.setattr(
        purchase_recommendations_module,
        "forecast_material",
        lambda *args, **kwargs: SimpleNamespace(forecast=[MagicMock()], dataset=[])
    )
    result = recomendar_momento_compra(material, 3, "alta", Decimal("100"), pricing_repo=object())
    assert result.decision == DECISION_MONITOREAR
    assert "no devolvio historial suficiente" in result.advertencias[0]


def test_evaluar_recomendacion_compra_branches() -> None:
    # variacion <= umbral_baja and criticidad in {baja, media} -> ESPERAR
    result = evaluar_recomendacion_compra(
        material_id=1, material_key="k", horizonte_meses=3, cantidad_objetivo=Decimal("1"),
        variacion_esperada_pct=Decimal("-10"), confiabilidad="alta", criticidad="baja", no_calibrado=False
    )
    assert result.decision == DECISION_ESPERAR
    
    # variacion <= umbral_baja and criticidad == alta -> ESPERAR
    result = evaluar_recomendacion_compra(
        material_id=1, material_key="k", horizonte_meses=3, cantidad_objetivo=Decimal("1"),
        variacion_esperada_pct=Decimal("-10"), confiabilidad="alta", criticidad="alta", no_calibrado=False
    )
    assert result.decision == DECISION_ESPERAR
    
    # decision == MONITOREAR and criticidad == alta and variacion >= umbral -> COMPRAR_AHORA
    result = evaluar_recomendacion_compra(
        material_id=1, material_key="k", horizonte_meses=3, cantidad_objetivo=Decimal("1"),
        variacion_esperada_pct=Decimal("10"), confiabilidad="alta", criticidad="alta", no_calibrado=False
    )
    assert result.decision == DECISION_COMPRAR_AHORA
    
    # decision == MONITOREAR and criticidad == baja and variacion <= umbral_baja -> ESPERAR
    result = evaluar_recomendacion_compra(
        material_id=1, material_key="k", horizonte_meses=3, cantidad_objetivo=Decimal("1"),
        variacion_esperada_pct=Decimal("-10"), confiabilidad="alta", criticidad="baja", no_calibrado=False
    )
    assert result.decision == DECISION_ESPERAR


def test_recomendar_momento_compra_material_key_from_selection(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Original", unidad_base="kg")
    selection = ForecastSelectionRead(
        material_key="key-personalizada",
        modelo_resuelto="m", regresores_resueltos=[], mape_referencia=Decimal("5"),
        mae_referencia=Decimal("5"), folds=1, confiabilidad="alta",
        origen_decision="o", justificacion="j", no_calibrado=False
    )
    mock_res = SimpleNamespace(
        dataset=[SimpleNamespace(ds=date(2024,1,1), y=100.0)],
        forecast=[SimpleNamespace(fecha=date(2024,2,1), precio_proyectado=Decimal("110"), precio_optimista=Decimal("105"), precio_pesimista=Decimal("115"))],
        metricas=SimpleNamespace(mape=Decimal("5")),
        seleccion_modelo=selection
    )
    monkeypatch.setattr(purchase_recommendations_module, "forecast_material", lambda *args, **kwargs: mock_res)
    
    result = recomendar_momento_compra(material, 3, "alta", Decimal("100"), pricing_repo=object())
    assert result.material_key == "key-personalizada"
