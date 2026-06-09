from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.chat.interfaces.schemas import CommercialProposalCreate
from app.modules.pricing.interfaces.schemas import (
    CommercialMarginCreate,
    CommercialMarginUpdate,
    ContextualPurchaseRecommendationCreate,
    PurchaseTemporalSimulationCreate,
)


def test_commercial_margin_create_global_with_data():
    with pytest.raises(ValidationError, match="El margen GLOBAL no debe tener"):
        CommercialMarginCreate(scope="GLOBAL", material_id=1, margen_ganancia_pct=Decimal("10"))

def test_commercial_margin_create_material_missing_id():
    with pytest.raises(ValidationError, match="El margen MATERIAL requiere material_id"):
        CommercialMarginCreate(scope="MATERIAL", material_id=None, margen_ganancia_pct=Decimal("10"))

def test_commercial_margin_create_material_with_extra():
    with pytest.raises(ValidationError, match="El margen MATERIAL no debe tener presentation_id"):
        CommercialMarginCreate(scope="MATERIAL", material_id=1, presentation_id=1, margen_ganancia_pct=Decimal("10"))

def test_commercial_margin_create_product_missing_data():
    with pytest.raises(ValidationError, match="El margen PRODUCT requiere material_id"):
        CommercialMarginCreate(scope="PRODUCT", material_id=None, margen_ganancia_pct=Decimal("10"))
    with pytest.raises(ValidationError, match="El margen PRODUCT requiere presentation_id o product_key"):
        CommercialMarginCreate(scope="PRODUCT", material_id=1, presentation_id=None, product_key=None, margen_ganancia_pct=Decimal("10"))

def test_commercial_margin_update_global_with_data():
    with pytest.raises(ValidationError, match="El margen GLOBAL no debe tener"):
        CommercialMarginUpdate(scope="GLOBAL", material_id=1)

def test_commercial_margin_update_material_missing_id():
    with pytest.raises(ValidationError, match="El margen MATERIAL requiere material_id"):
        CommercialMarginUpdate(scope="MATERIAL", material_id=None)

def test_commercial_margin_update_material_with_extra():
    with pytest.raises(ValidationError, match="El margen MATERIAL no debe tener presentation_id"):
        CommercialMarginUpdate(scope="MATERIAL", material_id=1, presentation_id=1)

def test_commercial_margin_update_product_missing_data():
    with pytest.raises(ValidationError, match="El margen PRODUCT requiere material_id"):
        CommercialMarginUpdate(scope="PRODUCT", material_id=None)
    with pytest.raises(ValidationError, match="El margen PRODUCT requiere presentation_id o product_key"):
        CommercialMarginUpdate(scope="PRODUCT", material_id=1, presentation_id=None, product_key=None)

def test_contextual_recommendation_create_validation():
    # None of them
    with pytest.raises(ValidationError, match="Debe informar fecha_objetivo_uso u horizonte_meses"):
        ContextualPurchaseRecommendationCreate(
            fase_obra="general", tolerancia_riesgo="media", cantidad_objetivo=Decimal("10")
        )
    # Both of them
    with pytest.raises(ValidationError, match="Informe fecha_objetivo_uso u horizonte_meses, no ambos"):
        ContextualPurchaseRecommendationCreate(
            fase_obra="general", tolerancia_riesgo="media", cantidad_objetivo=Decimal("10"),
            horizonte_meses=3, fecha_objetivo_uso=date(2024, 1, 1)
        )

def test_purchase_temporal_simulation_create_validation():
    # Invalid horizon
    with pytest.raises(ValidationError, match="Cada horizonte_meses debe estar entre 1 y 12"):
        PurchaseTemporalSimulationCreate(horizontes_meses=[0, 3], cantidad_objetivo=Decimal("10"))
    # Duplicated
    with pytest.raises(ValidationError, match="no puede tener valores duplicados"):
        PurchaseTemporalSimulationCreate(horizontes_meses=[3, 3], cantidad_objetivo=Decimal("10"))

def test_commercial_proposal_create_validation():
    # None of them
    with pytest.raises(ValidationError, match="Debe informar fecha_objetivo_uso u horizonte_meses"):
        CommercialProposalCreate(
            material_id=1, cantidad=Decimal("10"), fase_obra="general", tolerancia_riesgo="media"
        )
    # Both of them
    with pytest.raises(ValidationError, match="Informe fecha_objetivo_uso u horizonte_meses, no ambos"):
        CommercialProposalCreate(
            material_id=1, cantidad=Decimal("10"), fase_obra="general", tolerancia_riesgo="media",
            horizonte_meses=3, fecha_objetivo_uso=date(2024, 1, 1)
        )
