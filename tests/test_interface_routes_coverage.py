from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.modules.catalog.interfaces import fuentes, materiales, presentaciones
from app.modules.catalog.interfaces.schemas import FuenteCreate, MaterialCreate, PresentacionCreate
from app.modules.pricing.domain.exceptions import MaterialNotFoundException
from app.modules.pricing.interfaces import routes as pricing_routes
from app.modules.pricing.interfaces.schemas import (
    CommercialMarginCreate,
    CommercialMarginUpdate,
    ExternalIndexSyncRequest,
    MaterialCriticidadCreate,
    MaterialCriticidadItemCreate,
    PrecioHistoricoCreate,
    PriceImputationRequest,
    PurchaseOptimizationCreate,
    PurchaseOptimizationMaterialCreate,
    PurchaseRecommendationCreate,
    PurchaseStrategyComparisonCreate,
)


class FakeDb:
    def __init__(self, *, rows=None, material=None, fail_commit=False) -> None:
        self.rows = list(rows or [])
        self.material = material
        self.fail_commit = fail_commit
        self.added = []
        self.rolled_back = False

    def scalars(self, _stmt):
        return iter(self.rows)

    def get(self, _model, _id):
        return self.material

    def add(self, value):
        self.added.append(value)

    def commit(self):
        if self.fail_commit:
            raise IntegrityError("stmt", "params", Exception("duplicado"))

    def rollback(self):
        self.rolled_back = True

    def refresh(self, value):
        value.id = getattr(value, "id", 1)
        value.created_at = getattr(value, "created_at", datetime(2026, 1, 1))
        value.updated_at = getattr(value, "updated_at", datetime(2026, 1, 1))


def test_catalog_routes_listan_y_crean() -> None:
    rows = [SimpleNamespace(id=1)]
    assert materiales.listar_materiales(db=FakeDb(rows=rows), activos=True) == rows
    assert fuentes.listar_fuentes(db=FakeDb(rows=rows)) == rows
    assert presentaciones.listar_presentaciones(material_id=1, db=FakeDb(rows=rows)) == rows

    material = materiales.crear_material(
        MaterialCreate(nombre="Arena", unidad_base="kg"),
        db=FakeDb(),
    )
    assert material.nombre == "Arena"

    fuente = fuentes.crear_fuente(
        FuenteCreate(nombre="Factura"),
        db=FakeDb(),
    )
    assert fuente.nombre == "Factura"

    presentacion = presentaciones.crear_presentacion(
        PresentacionCreate(
            material_id=1,
            nombre_presentacion="Bolsa",
            cantidad_base=Decimal("25.0000"),
            unidad_presentacion="kg",
        ),
        db=FakeDb(material=SimpleNamespace(id=1)),
    )
    assert presentacion.nombre_presentacion == "Bolsa"


def test_catalog_routes_errores() -> None:
    for create_func, payload, detail in [
        (materiales.crear_material, MaterialCreate(nombre="Arena", unidad_base="kg"), "El material ya existe"),
        (fuentes.crear_fuente, FuenteCreate(nombre="Factura"), "La fuente ya existe"),
    ]:
        with pytest.raises(HTTPException) as exc:
            create_func(payload, db=FakeDb(fail_commit=True))
        assert exc.value.status_code == 409
        assert exc.value.detail == detail

    with pytest.raises(HTTPException) as missing_material:
        presentaciones.crear_presentacion(
            PresentacionCreate(
                material_id=1,
                nombre_presentacion="Bolsa",
                cantidad_base=Decimal("25.0000"),
                unidad_presentacion="kg",
            ),
            db=FakeDb(),
        )
    assert missing_material.value.status_code == 404

    with pytest.raises(HTTPException) as duplicated:
        presentaciones.crear_presentacion(
            PresentacionCreate(
                material_id=1,
                nombre_presentacion="Bolsa",
                cantidad_base=Decimal("25.0000"),
                unidad_presentacion="kg",
            ),
            db=FakeDb(material=SimpleNamespace(id=1), fail_commit=True),
        )
    assert duplicated.value.detail == "La presentacion ya existe para este material"


def test_pricing_routes_delegan_servicios_basicos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pricing_routes,
        "obtener_rango_precios_historicos_service",
        lambda _db: {
            "desde": date(2026, 1, 1),
            "hasta": date(2026, 2, 1),
            "hoy": date(2026, 5, 12),
            "tiene_fechas_futuras": False,
            "hasta_real": date(2026, 2, 1),
        },
    )
    assert pricing_routes.obtener_rango_precios_historicos(db=object()).hoy == date(2026, 5, 12)

    monkeypatch.setattr(pricing_routes, "listar_precios_historicos_service", lambda *args, **kwargs: ["precio"])
    assert pricing_routes.listar_precios_historicos(material_id=1, db=object()) == ["precio"]

    monkeypatch.setattr(pricing_routes, "list_external_indices", lambda *args, **kwargs: ["indice"])
    assert pricing_routes.listar_indices_externos(series_id="IPC", db=object()) == ["indice"]

    monkeypatch.setattr(
        pricing_routes,
        "sync_external_index",
        lambda *args, **kwargs: SimpleNamespace(source_name="IPC", series_id="S1", inserted=1, updated=2, unchanged=3),
    )
    sync = pricing_routes.sincronizar_indice_externo(
        ExternalIndexSyncRequest(source_name="IPC", series_id="S1"),
        db=object(),
        current_user=object(),
    )
    assert sync.inserted == 1


def test_pricing_routes_series_y_validaciones() -> None:
    material = SimpleNamespace(id=1, nombre="Arena", unidad_base="kg")
    price = SimpleNamespace(
        fecha=date(2026, 1, 10),
        precio_normalizado=Decimal("100"),
        fuente=None,
        numero_comprobante=None,
    )
    material_repo = SimpleNamespace(get_by_id=lambda material_id: material if material_id == 1 else None)
    pricing_repo = SimpleNamespace(get_historical_prices=lambda *_args: [price])

    assert pricing_routes.listar_precios_por_material(1, material_repo=material_repo, pricing_repo=pricing_repo) == [price]
    assert pricing_routes.obtener_serie_precios_material(
        1,
        agrupacion="mensual",
        material_repo=material_repo,
        pricing_repo=pricing_repo,
    )[0].precio_promedio_normalizado == Decimal("100.0000")

    with pytest.raises(MaterialNotFoundException):
        pricing_routes.listar_precios_por_material(2, material_repo=material_repo, pricing_repo=pricing_repo)
    with pytest.raises(HTTPException):
        pricing_routes.obtener_serie_precios_material(
            1,
            agrupacion="semana",
            material_repo=material_repo,
            pricing_repo=pricing_repo,
        )


def test_pricing_routes_decision_y_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    material = SimpleNamespace(id=1, nombre="Arena", unidad_base="kg")
    material_repo = SimpleNamespace(get_by_id=lambda _id: material)

    monkeypatch.setattr(
        pricing_routes,
        "recomendar_momento_compra",
        lambda *args, **kwargs: SimpleNamespace(
            material_id=1,
            material_key="arena",
            horizonte_meses=3,
            decision="MONITOREAR",
            variacion_esperada_pct=Decimal("1.00"),
            confiabilidad="media",
            criticidad="media",
            justificacion="Sin ventaja clara",
            advertencias=(),
        ),
    )
    recommendation = pricing_routes.recomendar_momento_compra_material(
        1,
        PurchaseRecommendationCreate(criticidad="media", cantidad_objetivo=Decimal("10.0000")),
        material_repo=material_repo,
        pricing_repo=object(),
    )
    assert recommendation.decision == "MONITOREAR"

    monkeypatch.setattr(
        pricing_routes,
        "comparar_estrategias_compra",
        lambda *args, **kwargs: SimpleNamespace(
            material_id=1,
            material_key="arena",
            horizonte_meses=3,
            cantidad_objetivo=Decimal("10.0000"),
            porcentaje_compra_inmediata=Decimal("0.5000"),
            precio_actual=Decimal("100"),
            precio_proyectado_horizonte=Decimal("110"),
            variacion_esperada_pct=Decimal("10"),
            confiabilidad="media",
            estrategias=[
                SimpleNamespace(
                    nombre="COMPRAR_AHORA",
                    costo_estimado=Decimal("1000"),
                    riesgo="bajo",
                    descripcion="Compra total",
                )
            ],
            mejor_estrategia="COMPRAR_AHORA",
            ahorro_estimado=Decimal("100"),
            justificacion="Conviene ahora",
            advertencias=(),
        ),
    )
    comparison = pricing_routes.comparar_estrategias_compra_material(
        1,
        PurchaseStrategyComparisonCreate(cantidad_objetivo=Decimal("10.0000")),
        material_repo=material_repo,
        pricing_repo=object(),
    )
    assert comparison.mejor_estrategia == "COMPRAR_AHORA"

    monkeypatch.setattr(
        pricing_routes,
        "optimizar_compra_con_presupuesto",
        lambda *args, **kwargs: SimpleNamespace(
            presupuesto_total=Decimal("1000"),
            presupuesto_utilizado=Decimal("500"),
            presupuesto_restante=Decimal("500"),
            horizonte_meses=3,
            estado_optimizacion="OPTIMAL",
            items=[],
            ahorro_total_estimado=Decimal("50"),
            justificacion="Asignacion parcial",
            advertencias=(),
        ),
    )
    optimization = pricing_routes.optimizar_presupuesto_compra(
        PurchaseOptimizationCreate(
            presupuesto_total=Decimal("1000.00"),
            materiales=[
                PurchaseOptimizationMaterialCreate(
                    material_id=1,
                    cantidad_objetivo=Decimal("10.0000"),
                    criticidad="media",
                )
            ],
        ),
        material_repo=material_repo,
        pricing_repo=object(),
    )
    assert optimization.estado_optimizacion == "OPTIMAL"

    with pytest.raises(HTTPException):
        pricing_routes.priorizar_materiales_por_criticidad(
            MaterialCriticidadCreate(
                alpha=Decimal("0.00"),
                beta=Decimal("0.00"),
                materiales=[MaterialCriticidadItemCreate(material_id=1, cantidad_requerida=Decimal("1.0000"))],
            ),
            material_repo=material_repo,
            pricing_repo=object(),
        )

    monkeypatch.setattr(
        pricing_routes,
        "priorizar_materiales_desde_forecast",
        lambda payload, material_repo, pricing_repo: SimpleNamespace(
            horizonte_meses=payload.horizonte_meses,
            alpha=payload.alpha,
            beta=payload.beta,
            materiales=[],
        ),
    )
    priority = pricing_routes.priorizar_materiales_por_criticidad(
        MaterialCriticidadCreate(
            materiales=[MaterialCriticidadItemCreate(material_id=1, cantidad_requerida=Decimal("1.0000"))],
        ),
        material_repo=material_repo,
        pricing_repo=object(),
    )
    assert priority.materiales == []


def test_pricing_routes_margenes_precio_comercial_imputacion_y_creacion(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 1, 1)
    margin = SimpleNamespace(
        id=1,
        scope="GLOBAL",
        material_id=None,
        presentation_id=None,
        product_key=None,
        margen_ganancia_pct=Decimal("10.00"),
        activo=True,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(pricing_routes, "listar_margenes_comerciales_service", lambda _db: [margin])
    monkeypatch.setattr(pricing_routes, "crear_margen_comercial_service", lambda _db, **_kwargs: margin)
    monkeypatch.setattr(pricing_routes, "actualizar_margen_comercial_service", lambda _db, **_kwargs: margin)

    assert len(pricing_routes.listar_margenes_comerciales(db=object(), current_user=object())) == 1
    assert pricing_routes.crear_margen_comercial(
        CommercialMarginCreate(scope="GLOBAL", margen_ganancia_pct=Decimal("10.00")),
        db=object(),
        current_user=object(),
    ).id == 1
    assert pricing_routes.actualizar_margen_comercial(
        1,
        CommercialMarginUpdate(activo=False),
        db=object(),
        current_user=object(),
    ).id == 1

    material = SimpleNamespace(id=1, nombre="Arena", unidad_base="kg")
    material_repo = SimpleNamespace(get_by_id=lambda _id: material)
    monkeypatch.setattr(
        pricing_routes,
        "calcular_precio_comercial",
        lambda **_kwargs: SimpleNamespace(
            material_id=1,
            material_key="arena",
            presentation_id=None,
            product_key=None,
            costo_base_actual=Decimal("100"),
            costo_base_proyectado=Decimal("110"),
            margen_ganancia_pct=Decimal("10"),
            origen_margen="GLOBAL",
            precio_final_actual=Decimal("110"),
            precio_final_proyectado=Decimal("121"),
            ganancia_unitaria_actual=Decimal("10"),
            ganancia_unitaria_proyectada=Decimal("11"),
            advertencias=(),
        ),
    )
    assert pricing_routes.obtener_precio_comercial_material(
        1,
        material_repo=material_repo,
        pricing_repo=object(),
        db=object(),
    ).precio_final_actual == Decimal("110")

    monkeypatch.setattr(
        pricing_routes,
        "impute_monthly_prices",
        lambda *args, **kwargs: SimpleNamespace(
            material_id=1,
            source_name="IPC",
            series_id="IPC",
            metodo_estimacion="IPC",
            inserted=1,
            updated=0,
            skipped_real_months=0,
            generated_months=[date(2026, 1, 1)],
        ),
    )
    imputation = pricing_routes.imputar_precios_material(
        1,
        PriceImputationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            index_series_id="IPC",
            source_name="IPC",
            metodo_estimacion="IPC",
        ),
        db=object(),
        current_user=object(),
    )
    assert imputation.inserted == 1

    monkeypatch.setattr(pricing_routes, "crear_precio_historico_service", lambda _db, **kwargs: kwargs)
    created = pricing_routes.crear_precio_historico(
        PrecioHistoricoCreate(material_id=1, fecha=date(2026, 1, 1), precio_original=Decimal("100.00")),
        db=object(),
        current_user=object(),
    )
    assert created["material_id"] == 1
