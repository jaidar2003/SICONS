from datetime import date
from types import SimpleNamespace
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.modules.pricing.application import forecast_service
from app.modules.pricing.application.forecast_service import (
    FORECAST_MODEL_NAME,
    ForecastMaterialResult,
    _resolver_plan_ejecucion,
    construir_firma_dataset,
    forecast_material,
    limpiar_forecast_cache,
)
from app.modules.catalog.application.utils import derive_material_key
from app.modules.pricing.application.model_selector import resolve_model_selection as resolve_selector_model
from app.modules.pricing.application.forecasting import ProphetRow
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead, ForecastSelectionRead
from app.modules.pricing.interfaces.routes import obtener_forecast_material


def _forecast_result(
    valor: str,
    *,
    modelo: str = FORECAST_MODEL_NAME,
    seleccion_modelo: ForecastSelectionRead | None = None,
    supuesto_regresores: str = "nota",
) -> ForecastMaterialResult:
    return ForecastMaterialResult(
        dataset=[ProphetRow(ds=date(2024, 1, 1), y=float(valor))],
        metricas=ForecastMetricasRead(
            folds=1,
            mae=Decimal("1.00"),
            mape=Decimal("2.00"),
            efectividad_informal=Decimal("98.00"),
        ),
        forecast=[
            ForecastPuntoRead(
                fecha=date(2024, 2, 1),
                precio_proyectado=Decimal(valor),
                precio_equivalente_25kg=Decimal("2500.00"),
                precio_equivalente_50kg=Decimal("5000.00"),
            )
        ],
        modelo=modelo,
        supuesto_regresores=supuesto_regresores,
        seleccion_modelo=seleccion_modelo,
    )


def test_construir_firma_dataset_cambia_si_cambia_la_serie() -> None:
    firma_a = construir_firma_dataset([ProphetRow(ds=date(2024, 1, 1), y=100.0)])
    firma_b = construir_firma_dataset([ProphetRow(ds=date(2024, 1, 1), y=101.0)])
    assert firma_a != firma_b


def test_forecast_material_reutiliza_cache_para_la_misma_serie(monkeypatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30
    llamadas = {"cantidad": 0}

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda material, db: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.construir_dataset_prophet",
        lambda puntos, objetivo: dataset,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, columnas: {"columnas": columnas},
    )

    def fake_forecast(material, horizonte_meses, dataset, pd, prophet, plan):
        llamadas["cantidad"] += 1
        return _forecast_result("110.00", modelo=plan.modelo, supuesto_regresores=plan.supuesto_regresores)

    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    primer = forecast_material(material, 3, object())
    segundo = forecast_material(material, 3, object())

    assert llamadas["cantidad"] == 1
    assert primer.forecast[0].precio_proyectado == Decimal("110.00")
    assert segundo.forecast[0].precio_proyectado == Decimal("110.00")


def test_forecast_material_invalida_cache_si_cambia_el_dataset(monkeypatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    datasets = [
        [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30,
        [ProphetRow(ds=date(2024, 1, 1), y=101.0)] * 30,
    ]
    resultados = iter([_forecast_result("110.00"), _forecast_result("115.00")])
    llamadas = {"cantidad": 0}

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda material, db: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, columnas: {"columnas": columnas},
    )

    def fake_dataset(puntos, objetivo):
        return datasets.pop(0)

    def fake_forecast(material, horizonte_meses, dataset, pd, prophet, plan):
        llamadas["cantidad"] += 1
        result = next(resultados)
        return _forecast_result(
            str(result.forecast[0].precio_proyectado),
            modelo=plan.modelo,
            supuesto_regresores=plan.supuesto_regresores,
        )

    monkeypatch.setattr("app.modules.pricing.application.forecast_service.construir_dataset_prophet", fake_dataset)
    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    primer = forecast_material(material, 3, object())
    segundo = forecast_material(material, 3, object())

    assert llamadas["cantidad"] == 2
    assert primer.forecast[0].precio_proyectado == Decimal("110.00")
    assert segundo.forecast[0].precio_proyectado == Decimal("115.00")


def test_forecast_con_selector_desactivado_mantiene_comportamiento_actual(monkeypatch: pytest.MonkeyPatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda _material, _repo: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda _cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda _cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.construir_dataset_prophet",
        lambda puntos, objetivo: dataset,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, columnas: {"columnas": columnas},
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("El selector no deberia ejecutarse cuando esta desactivado.")

    monkeypatch.setattr("app.modules.pricing.application.forecast_service.resolve_model_selection", fail_if_called)

    def fake_forecast(_material, _horizonte, _dataset, _pd, _prophet, plan):
        return _forecast_result("110.00", modelo=plan.modelo, supuesto_regresores=plan.supuesto_regresores)

    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    result = forecast_material(material, 3, object(), usar_selector_modelo=False)

    assert result.modelo == FORECAST_MODEL_NAME
    assert result.seleccion_modelo is None


@pytest.mark.parametrize(
    ("material_id", "nombre", "modelo", "regresores"),
    [
        (1, "Cemento Portland", "prophet_ipim_icc_var_materials", ("ipim_nivel_general", "icc_var_materials")),
        (4, "Pastina", "prophet_ipim_cac_labour_force", ("ipim_nivel_general", "cac_labour_force")),
        (10, "Membrana Megaflex", "prophet_ipim_icc_var_general", ("ipim_nivel_general", "icc_var_general")),
    ],
)
def test_selector_activado_usa_modelo_recomendado(monkeypatch: pytest.MonkeyPatch, material_id: int, nombre: str, modelo: str, regresores: tuple[str, ...]) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=material_id, nombre=nombre, unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30
    material_key_esperado = derive_material_key(nombre)
    llamadas: list[tuple[str, int]] = []

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda _material, _repo: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda _cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda _cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.construir_dataset_prophet",
        lambda puntos, objetivo: dataset,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, columnas: {"columnas": columnas},
    )
    def fake_resolve_model_selection(material_key: str, horizonte_meses: int):
        llamadas.append((material_key, horizonte_meses))
        return resolve_selector_model(material_key, horizonte_meses)

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.resolve_model_selection",
        fake_resolve_model_selection,
    )

    def fake_forecast(_material, _horizonte, _dataset, _pd, _prophet, plan):
        return _forecast_result(
            "110.00",
            modelo=plan.modelo,
            supuesto_regresores=plan.supuesto_regresores,
            seleccion_modelo=plan.seleccion_modelo,
        )

    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    result = forecast_material(material, 3, object(), usar_selector_modelo=True)

    assert result.modelo == modelo
    assert llamadas == [(material_key_esperado, 3)]
    assert result.seleccion_modelo is not None
    assert result.seleccion_modelo.material_key == material_key_esperado
    assert result.seleccion_modelo.modelo_resuelto == modelo
    assert tuple(result.seleccion_modelo.regresores_resueltos) == regresores
    assert result.seleccion_modelo.no_calibrado is False


def test_material_no_calibrado_cae_a_prophet_base(monkeypatch: pytest.MonkeyPatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=999, nombre="Material sin calibrar", unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda _material, _repo: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda _cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda _cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.construir_dataset_prophet",
        lambda puntos, objetivo: dataset,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )

    def fake_forecast(_material, _horizonte, _dataset, _pd, _prophet, plan):
        return _forecast_result(
            "110.00",
            modelo=plan.modelo,
            supuesto_regresores=plan.supuesto_regresores,
            seleccion_modelo=plan.seleccion_modelo,
        )

    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    result = forecast_material(material, 3, object(), usar_selector_modelo=True)

    assert result.modelo == "prophet_base"
    assert result.seleccion_modelo is not None
    assert result.seleccion_modelo.material_key == "material-sin-calibrar"
    assert result.seleccion_modelo.no_calibrado is True


def test_selector_activado_hace_fallback_por_material_si_no_hay_horizonte_exacto(monkeypatch: pytest.MonkeyPatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=4, nombre="Pastina", unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda _material, _repo: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda _cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda _cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.construir_dataset_prophet",
        lambda puntos, objetivo: dataset,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, columnas: {"columnas": columnas},
    )

    def fake_forecast(_material, _horizonte, _dataset, _pd, _prophet, plan):
        return _forecast_result(
            "110.00",
            modelo=plan.modelo,
            supuesto_regresores=plan.supuesto_regresores,
            seleccion_modelo=plan.seleccion_modelo,
        )

    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    result = forecast_material(material, 5, object(), usar_selector_modelo=True)

    assert result.modelo == "prophet_ipim_cac_labour_force"
    assert result.seleccion_modelo is not None
    assert result.seleccion_modelo.material_key == "pastina"
    assert result.seleccion_modelo.origen_decision == "material_default"
    assert result.seleccion_modelo.no_calibrado is True


def test_regresor_faltante_no_rompe_el_forecast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, _columnas: (_ for _ in ()).throw(HTTPException(status_code=500, detail="Regresor faltante")),
    )

    selection = _resolver_plan_ejecucion(material_key="cemento-portland", horizonte_meses=3, usar_selector_modelo=True, pd=object())

    assert selection.modelo == "prophet_base"
    assert selection.seleccion_modelo is not None
    assert selection.seleccion_modelo.material_key == "cemento-portland"
    assert selection.seleccion_modelo.no_calibrado is True
    assert selection.seleccion_modelo.advertencia is not None


def test_regresor_faltante_no_rompe_el_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    monkeypatch.setattr("app.modules.pricing.interfaces.routes.USAR_SELECTOR_MODELO_FORECAST", True)
    monkeypatch.setattr(
        "app.modules.pricing.interfaces.routes.forecast_material",
        lambda _material, _horizonte, _repo, usar_selector_modelo=False: _forecast_result(
            "110.00",
            modelo="prophet_base",
            supuesto_regresores="Fallback controlado a prophet_base por regresores no disponibles.",
            seleccion_modelo=ForecastSelectionRead(
                modelo_resuelto="prophet_base",
                regresores_resueltos=[],
                mape_referencia=None,
                mae_referencia=None,
                folds=None,
                confiabilidad="no_calibrada",
                origen_decision="fallback_regresores",
                justificacion="Se degrada a prophet_base por faltante operativo de regresores.",
                no_calibrado=True,
                advertencia="Regresor faltante",
                material_key="cemento-portland",
            ),
        ),
    )

    response = obtener_forecast_material(
        1,
        3,
        material_repo=SimpleNamespace(get_by_id=lambda _material_id: material),
        pricing_repo=object(),
    )

    assert response.modelo == "prophet_base"
    assert response.seleccion_modelo is not None
    assert response.seleccion_modelo.advertencia == "Regresor faltante"
    assert response.seleccion_modelo.material_key == "cemento-portland"


def test_respuesta_expone_metadatos_de_seleccion_cuando_corresponde(monkeypatch: pytest.MonkeyPatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    selection = ForecastSelectionRead(
        modelo_resuelto="prophet_ipim_nivel_general",
        regresores_resueltos=["ipim_nivel_general"],
        mape_referencia=Decimal("4.98"),
        mae_referencia=Decimal("6.76"),
        folds=9,
        confiabilidad="alta",
        origen_decision="material_horizonte",
        justificacion="Configuracion recomendada.",
        no_calibrado=False,
        material_key="cemento-portland",
    )

    monkeypatch.setattr("app.modules.pricing.interfaces.routes.USAR_SELECTOR_MODELO_FORECAST", True)
    monkeypatch.setattr(
        "app.modules.pricing.interfaces.routes.forecast_material",
        lambda _material, _horizonte, _repo, usar_selector_modelo=False: _forecast_result(
            "110.00",
            modelo="prophet_ipim_nivel_general",
            supuesto_regresores="Regresores resueltos: ipim_nivel_general.",
            seleccion_modelo=selection,
        ),
    )

    response = obtener_forecast_material(
        1,
        3,
        material_repo=SimpleNamespace(get_by_id=lambda _material_id: material),
        pricing_repo=object(),
    )

    assert response.modelo == "prophet_ipim_nivel_general"
    assert response.seleccion_modelo is not None
    assert response.seleccion_modelo.modelo_resuelto == "prophet_ipim_nivel_general"
    assert response.seleccion_modelo.mape_referencia == Decimal("4.98")
    assert response.seleccion_modelo.material_key == "cemento-portland"


def test_normalizacion_por_kg_no_cambia_con_selector_activado(monkeypatch: pytest.MonkeyPatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30
    objetivo_usado = {"valor": None}

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda _material, _repo: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_forecast_snapshot",
        lambda _cache_key: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.guardar_forecast_snapshot",
        lambda _cache_key, result: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.cargar_regresores_mensuales",
        lambda _pd, columnas: {"columnas": columnas},
    )

    def fake_dataset(_puntos, objetivo):
        objetivo_usado["valor"] = objetivo
        return dataset

    def fake_forecast(_material, _horizonte, _dataset, _pd, _prophet, plan):
        return _forecast_result(
            "110.00",
            modelo=plan.modelo,
            supuesto_regresores=plan.supuesto_regresores,
            seleccion_modelo=plan.seleccion_modelo,
        )

    monkeypatch.setattr("app.modules.pricing.application.forecast_service.construir_dataset_prophet", fake_dataset)
    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    forecast_material(material, 3, object(), usar_selector_modelo=True)

    assert objetivo_usado["valor"] == "precio_promedio_normalizado"
