from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.shared.api.exception_handlers import register_exception_handlers
from app.modules.pricing.domain.exceptions import (
    MaterialNotFoundException,
    InsufficientDataException,
    ExternalRegressorError,
    ExternalIndexSyncError,
    PriceImputationError,
    PricingDomainException,
)

def test_exception_handlers():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/material-not-found")
    def trigger_material_not_found():
        raise MaterialNotFoundException(1)

    @app.get("/insufficient-data")
    def trigger_insufficient_data():
        raise InsufficientDataException("Datos insuficientes")

    @app.get("/external-regressor")
    def trigger_external_regressor():
        raise ExternalRegressorError("Error en regresores")

    @app.get("/external-index-sync")
    def trigger_external_index_sync():
        raise ExternalIndexSyncError("Error en sincronización")

    @app.get("/price-imputation")
    def trigger_price_imputation():
        raise PriceImputationError("Error en imputación")

    @app.get("/pricing-domain")
    def trigger_pricing_domain():
        raise PricingDomainException("Error de dominio")

    client = TestClient(app)

    response = client.get("/material-not-found")
    assert response.status_code == 404
    assert response.json() == {"detail": "Material with ID 1 not found."}

    response = client.get("/insufficient-data")
    assert response.status_code == 422
    assert response.json() == {"detail": "Datos insuficientes"}

    response = client.get("/external-regressor")
    assert response.status_code == 422
    assert response.json() == {"detail": "Error en regresores"}

    response = client.get("/external-index-sync")
    assert response.status_code == 502
    assert response.json() == {"detail": "Error en sincronización"}

    response = client.get("/price-imputation")
    assert response.status_code == 422
    assert response.json() == {"detail": "Error en imputación"}

    response = client.get("/pricing-domain")
    assert response.status_code == 400
    assert response.json() == {"detail": "Error de dominio"}
