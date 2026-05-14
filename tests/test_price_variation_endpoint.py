from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.interfaces.dependencies import get_pricing_repository


def test_endpoint_variacion_entre_fechas_devuelve_comparacion_libre() -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    class FakeMaterialRepo:
        def get_by_id(self, material_id: int):
            return material if material_id == 1 else None

    class FakePricingRepo:
        def get_historical_prices(self, material_id: int, _desde):
            if material_id != 1:
                return []
            return [
                SimpleNamespace(
                    fecha=date(2026, 1, 10),
                    precio_normalizado=Decimal("100.0000"),
                    fuente=SimpleNamespace(nombre="Factura compra"),
                    numero_comprobante="A-1",
                ),
                SimpleNamespace(
                    fecha=date(2026, 2, 5),
                    precio_normalizado=Decimal("110.0000"),
                    fuente=SimpleNamespace(nombre="Factura compra"),
                    numero_comprobante="A-2",
                ),
                SimpleNamespace(
                    fecha=date(2026, 3, 20),
                    precio_normalizado=Decimal("121.0000"),
                    fuente=SimpleNamespace(nombre="Factura compra"),
                    numero_comprobante="A-3",
                ),
            ]

    app.dependency_overrides[get_material_repository] = lambda: FakeMaterialRepo()
    app.dependency_overrides[get_pricing_repository] = lambda: FakePricingRepo()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")

    try:
        client = TestClient(app)
        response = client.get(
            "/materiales/1/variacion-entre-fechas",
            params={"fecha_desde": "2026-02-01", "fecha_hasta": "2026-03-31"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["material_id"] == 1
    assert body["fecha_desde_solicitada"] == "2026-02-01"
    assert body["fecha_hasta_solicitada"] == "2026-03-31"
    assert body["fecha_desde_usada"] == "2026-01-10"
    assert body["fecha_hasta_usada"] == "2026-03-20"
    assert body["precio_desde"] == "100.0000"
    assert body["precio_hasta"] == "121.0000"
    assert body["variacion_porcentual"] == "21.0000"
