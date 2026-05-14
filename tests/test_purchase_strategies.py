from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.application import purchase_strategies as purchase_strategies_module
from app.modules.pricing.application.purchase_recommendations import CONFIANZA_ALTA, CONFIANZA_BAJA
from app.modules.pricing.application.purchase_strategies import (
    ESTRATEGIA_COMPRA_PARCIAL,
    ESTRATEGIA_COMPRAR_AHORA,
    ESTRATEGIA_ESPERAR_AL_HORIZONTE,
    comparar_estrategias_compra,
    evaluar_estrategias_compra,
)
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead, ForecastSelectionRead


def _fake_forecast_result(
    *,
    actual: str = "1000.00",
    proyectado: str = "1084.00",
    confiabilidad: str = CONFIANZA_ALTA,
    no_calibrado: bool = False,
    advertencia: str | None = None,
):
    return SimpleNamespace(
        dataset=[SimpleNamespace(ds=date(2024, 1, 1), y=float(actual))],
        forecast=[ForecastPuntoRead(fecha=date(2024, 4, 1), precio_proyectado=Decimal(proyectado))],
        metricas=ForecastMetricasRead(
            folds=9,
            mae=Decimal("6.76"),
            mape=Decimal("4.98"),
            efectividad_informal=Decimal("95.02"),
        ),
        seleccion_modelo=ForecastSelectionRead(
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
            advertencia=advertencia,
        ),
    )


def test_si_el_precio_proyectado_sube_comprar_ahora_es_la_mejor_estrategia() -> None:
    result = evaluar_estrategias_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        precio_actual=Decimal("1000"),
        precio_proyectado_horizonte=Decimal("1084"),
        confiabilidad=CONFIANZA_ALTA,
        no_calibrado=False,
    )

    assert result.mejor_estrategia == ESTRATEGIA_COMPRAR_AHORA
    assert result.estrategias[0].costo_estimado == Decimal("100000.00")
    assert result.estrategias[1].costo_estimado == Decimal("108400.00")
    assert result.estrategias[1].diferencia_vs_mejor_ars == Decimal("8400.00")
    assert result.estrategias[1].diferencia_vs_mejor_pct == Decimal("8.4000")
    assert result.umbral_decision_pct == Decimal("5.0000")
    assert result.ventaja_significativa is True


def test_si_el_precio_proyectado_baja_esperar_es_la_mejor_estrategia() -> None:
    result = evaluar_estrategias_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        precio_actual=Decimal("1000"),
        precio_proyectado_horizonte=Decimal("920"),
        confiabilidad=CONFIANZA_ALTA,
        no_calibrado=False,
    )

    assert result.mejor_estrategia == ESTRATEGIA_ESPERAR_AL_HORIZONTE


def test_compra_parcial_queda_entre_ahora_y_esperar_con_50_50() -> None:
    result = evaluar_estrategias_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        precio_actual=Decimal("1000"),
        precio_proyectado_horizonte=Decimal("1084"),
        confiabilidad=CONFIANZA_ALTA,
        no_calibrado=False,
        porcentaje_compra_inmediata=Decimal("0.50"),
    )

    costos = {estrategia.nombre: estrategia.costo_estimado for estrategia in result.estrategias}
    assert result.porcentaje_compra_inmediata == Decimal("0.50")
    assert costos[ESTRATEGIA_COMPRAR_AHORA] < costos[ESTRATEGIA_COMPRA_PARCIAL] < costos[ESTRATEGIA_ESPERAR_AL_HORIZONTE]


def test_compra_parcial_calcula_correctamente_con_porcentaje_personalizado() -> None:
    result = evaluar_estrategias_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        precio_actual=Decimal("1000"),
        precio_proyectado_horizonte=Decimal("1084"),
        confiabilidad=CONFIANZA_ALTA,
        no_calibrado=False,
        porcentaje_compra_inmediata=Decimal("0.30"),
    )

    costos = {estrategia.nombre: estrategia.costo_estimado for estrategia in result.estrategias}
    assert result.porcentaje_compra_inmediata == Decimal("0.30")
    assert costos[ESTRATEGIA_COMPRA_PARCIAL] == Decimal("105880.00")


def test_cantidad_objetivo_impacta_proporcionalmente_en_los_costos() -> None:
    base = evaluar_estrategias_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("100"),
        precio_actual=Decimal("1000"),
        precio_proyectado_horizonte=Decimal("1084"),
        confiabilidad=CONFIANZA_ALTA,
        no_calibrado=False,
    )
    doble = evaluar_estrategias_compra(
        material_id=1,
        material_key="cemento-portland",
        horizonte_meses=3,
        cantidad_objetivo=Decimal("200"),
        precio_actual=Decimal("1000"),
        precio_proyectado_horizonte=Decimal("1084"),
        confiabilidad=CONFIANZA_ALTA,
        no_calibrado=False,
    )

    costos_base = {estrategia.nombre: estrategia.costo_estimado for estrategia in base.estrategias}
    costos_doble = {estrategia.nombre: estrategia.costo_estimado for estrategia in doble.estrategias}
    assert costos_doble[ESTRATEGIA_COMPRAR_AHORA] == costos_base[ESTRATEGIA_COMPRAR_AHORA] * 2
    assert costos_doble[ESTRATEGIA_ESPERAR_AL_HORIZONTE] == costos_base[ESTRATEGIA_ESPERAR_AL_HORIZONTE] * 2
    assert costos_doble[ESTRATEGIA_COMPRA_PARCIAL] == costos_base[ESTRATEGIA_COMPRA_PARCIAL] * 2


def test_porcentaje_compra_inmediata_invalido_falla_en_el_schema(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result()
    monkeypatch.setattr(purchase_strategies_module, "forecast_material", lambda *args, **kwargs: fake_forecast_result)

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
            "/materiales/1/comparacion-estrategias-compra",
            json={"horizonte_meses": 3, "cantidad_objetivo": 100, "porcentaje_compra_inmediata": 1.2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_baja_confiabilidad_o_no_calibrado_devuelve_advertencia_metodologica(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result(confiabilidad=CONFIANZA_BAJA, no_calibrado=True, advertencia="Fallback controlado.")
    monkeypatch.setattr(purchase_strategies_module, "forecast_material", lambda *args, **kwargs: fake_forecast_result)

    result = comparar_estrategias_compra(
        material,
        3,
        Decimal("100"),
        pricing_repo=object(),
        usar_selector_modelo=False,
    )

    assert result.advertencias
    assert any("metodologicamente debil" in advertencia.lower() for advertencia in result.advertencias)
    assert "orientativa" in result.justificacion.lower()


def test_endpoint_responde_con_contrato_esperado(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result(actual="1000.00", proyectado="1084.00")
    monkeypatch.setattr(purchase_strategies_module, "forecast_material", lambda *args, **kwargs: fake_forecast_result)

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
            "/materiales/1/comparacion-estrategias-compra",
            json={"horizonte_meses": 3, "cantidad_objetivo": 100},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["material_id"] == 1
    assert body["material_key"] == "cemento-portland"
    assert body["mejor_estrategia"] == ESTRATEGIA_COMPRAR_AHORA
    assert body["porcentaje_compra_inmediata"] == "0.50"
    assert body["precio_actual"] == "1000.00"
    assert body["precio_proyectado_horizonte"] == "1084.00"
    assert body["ahorro_estimado"] == "8400.00"
    assert body["umbral_decision_pct"] == "5.0000"
    assert body["ventaja_significativa"] is True
    assert len(body["estrategias"]) == 3
    assert body["estrategias"][1]["diferencia_vs_mejor_ars"] == "8400.00"
    assert body["estrategias"][1]["diferencia_vs_mejor_pct"] == "8.4000"


def test_endpoint_devuelve_porcentaje_compra_inmediata_personalizado(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    fake_forecast_result = _fake_forecast_result(actual="1000.00", proyectado="1084.00")
    monkeypatch.setattr(purchase_strategies_module, "forecast_material", lambda *args, **kwargs: fake_forecast_result)

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
            "/materiales/1/comparacion-estrategias-compra",
            json={"horizonte_meses": 3, "cantidad_objetivo": 100, "porcentaje_compra_inmediata": 0.3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["porcentaje_compra_inmediata"]) == Decimal("0.30")
    parcial = next(estrategia for estrategia in body["estrategias"] if estrategia["nombre"] == ESTRATEGIA_COMPRA_PARCIAL)
    assert parcial["costo_estimado"] == "105880.00"


def test_endpoint_simulacion_escenarios_temporales_devuelve_multiples_horizontes(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    def fake_forecast(_material, horizonte, *_args, **_kwargs):
        proyectados = {3: "1084.00", 6: "1150.00", 12: "1300.00"}
        return _fake_forecast_result(actual="1000.00", proyectado=proyectados[horizonte])

    monkeypatch.setattr(purchase_strategies_module, "forecast_material", fake_forecast)

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
            "/materiales/1/simulacion-escenarios-compra",
            json={
                "horizontes_meses": [3, 6, 12],
                "cantidad_objetivo": 100,
                "porcentaje_compra_inmediata": 0.5,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["material_id"] == 1
    assert [item["horizonte_meses"] for item in body["simulaciones"]] == [3, 6, 12]
    assert all(item["mejor_estrategia"] == ESTRATEGIA_COMPRAR_AHORA for item in body["simulaciones"])


def test_hu22_no_usa_pulp_ni_ortools() -> None:
    source = inspect.getsource(purchase_strategies_module).lower()
    assert "pulp" not in source
    assert "ortools" not in source
