from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.modules.pricing.application.purchase_recommendations import (
    CONFIANZA_BAJA,
    CONFIANZA_ALTA,
    CONFIANZA_MEDIA,
    CONFIANZA_MEDIA_BAJA,
    DECISION_COMPRAR_AHORA,
    DECISION_ESPERAR,
    DECISION_MONITOREAR,
    evaluar_recomendacion_compra,
    recomendar_momento_compra,
)
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead, ForecastSelectionRead
from app.modules.pricing.application import purchase_recommendations as purchase_recommendations_module
from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.interfaces.dependencies import get_pricing_repository


def _fake_forecast_result(
    *,
    actual: str = "100.00",
    proyectado: str = "108.40",
    confiabilidad: str = CONFIANZA_ALTA,
    no_calibrado: bool = False,
    seleccion_modelo: ForecastSelectionRead | None = None,
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
    assert body["advertencias"] == []
