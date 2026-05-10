from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.modules.pricing.application import commercial_prices
from app.modules.pricing.application.commercial_prices import (
    CommercialMarginCandidate,
    calcular_precio_comercial,
    calcular_precio_final,
    resolve_commercial_margin,
)


def _candidate(
    *,
    id: int,
    scope: str,
    material_id: int | None = None,
    presentation_id: int | None = None,
    product_key: str | None = None,
    margin: str,
    updated_at: datetime | None = None,
    activo: bool = True,
) -> CommercialMarginCandidate:
    return CommercialMarginCandidate(
        id=id,
        scope=scope,
        material_id=material_id,
        presentation_id=presentation_id,
        product_key=product_key,
        margen_ganancia_pct=Decimal(margin),
        activo=activo,
        updated_at=updated_at or datetime(2026, 5, 9, tzinfo=UTC),
    )


def test_resolve_commercial_margin_prefiere_product_sobre_material_y_global() -> None:
    product_key = "cemento-portland-bolsa-25-kg"
    candidates = [
        _candidate(id=1, scope="GLOBAL", margin="20.00"),
        _candidate(id=2, scope="MATERIAL", material_id=1, margin="25.00"),
        _candidate(id=3, scope="PRODUCT", material_id=1, presentation_id=2, product_key=product_key, margin="28.00"),
    ]

    resolved = resolve_commercial_margin(
        candidates,
        material_id=1,
        presentation_id=2,
        product_key=product_key,
    )

    assert resolved is not None
    assert resolved.scope == "PRODUCT"
    assert resolved.margen_ganancia_pct == Decimal("28.00")


def test_resolve_commercial_margin_usa_material_si_no_hay_product() -> None:
    candidates = [
        _candidate(id=1, scope="GLOBAL", margin="20.00"),
        _candidate(id=2, scope="MATERIAL", material_id=1, margin="25.00"),
    ]

    resolved = resolve_commercial_margin(
        candidates,
        material_id=1,
        presentation_id=2,
        product_key="otro-producto",
    )

    assert resolved is not None
    assert resolved.scope == "MATERIAL"
    assert resolved.margen_ganancia_pct == Decimal("25.00")


def test_resolve_commercial_margin_usa_global_si_no_hay_otros() -> None:
    candidates = [_candidate(id=1, scope="GLOBAL", margin="20.00")]

    resolved = resolve_commercial_margin(
        candidates,
        material_id=1,
        presentation_id=None,
        product_key=None,
    )

    assert resolved is not None
    assert resolved.scope == "GLOBAL"
    assert resolved.margen_ganancia_pct == Decimal("20.00")


def test_calcular_precio_final_aplica_markup() -> None:
    assert calcular_precio_final(Decimal("1000.00"), Decimal("25.00")) == Decimal("1250.00")


def test_calcular_precio_comercial_aplica_margen_y_calcula_proyeccion(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland")
    presentation = SimpleNamespace(id=2, material_id=1, nombre_presentacion="Bolsa 25 kg")
    candidates = [
        _candidate(id=1, scope="GLOBAL", margin="20.00"),
        _candidate(id=2, scope="MATERIAL", material_id=1, margin="25.00"),
        _candidate(
            id=3,
            scope="PRODUCT",
            material_id=1,
            presentation_id=2,
            product_key="cemento-portland-bolsa-25-kg",
            margin="28.00",
        ),
    ]

    monkeypatch.setattr(
        commercial_prices,
        "_cargar_historial_base",
        lambda _pricing_repo, _material_id, _presentation_id=None: SimpleNamespace(precio_normalizado=Decimal("1000.00")),
    )
    monkeypatch.setattr(
        commercial_prices,
        "_cargar_candidatos",
        lambda _db: candidates,
    )
    monkeypatch.setattr(
        commercial_prices,
        "forecast_material",
        lambda _material, _horizonte, _pricing_repo, usar_selector_modelo=True: SimpleNamespace(
            forecast=[SimpleNamespace(precio_proyectado=Decimal("1200.00"))]
        ),
    )

    result = calcular_precio_comercial(
        material=material,
        pricing_repo=object(),
        db=SimpleNamespace(get=lambda model, item_id: presentation if item_id == presentation.id else None),
        horizonte_meses=3,
        presentation_id=2,
    )

    assert result.margen_ganancia_pct == Decimal("28.00")
    assert result.origen_margen == "PRODUCT"
    assert result.costo_base_actual == Decimal("1000.00")
    assert result.costo_base_proyectado == Decimal("1200.00")
    assert result.precio_final_actual == Decimal("1280.00")
    assert result.precio_final_proyectado == Decimal("1536.00")
    assert result.ganancia_unitaria_actual == Decimal("280.00")
    assert result.ganancia_unitaria_proyectada == Decimal("336.00")
    assert result.advertencias == ()


def test_calcular_precio_comercial_reutiliza_historico_del_material_si_no_hay_presentacion(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Pastina")
    presentation = SimpleNamespace(id=2, material_id=1, nombre_presentacion="Bolsa 1 kg")

    monkeypatch.setattr(
        commercial_prices,
        "_cargar_candidatos",
        lambda _db: [_candidate(id=1, scope="MATERIAL", material_id=1, margin="30.00")],
    )
    monkeypatch.setattr(
        commercial_prices,
        "forecast_material",
        lambda _material, _horizonte, _pricing_repo, usar_selector_modelo=True: SimpleNamespace(forecast=[]),
    )

    pricing_repo = SimpleNamespace(
        get_historical_prices=lambda _material_id, _since: [
            SimpleNamespace(id=10, fecha=date(2026, 1, 1), presentacion_id=None, precio_normalizado=Decimal("500.00")),
            SimpleNamespace(id=11, fecha=date(2026, 2, 1), presentacion_id=None, precio_normalizado=Decimal("520.00")),
        ]
    )

    result = calcular_precio_comercial(
        material=material,
        pricing_repo=pricing_repo,
        db=SimpleNamespace(get=lambda model, item_id: presentation if item_id == presentation.id else None),
        horizonte_meses=3,
        presentation_id=2,
    )

    assert result.costo_base_actual == Decimal("520.00")
    assert result.margen_ganancia_pct == Decimal("30.00")
