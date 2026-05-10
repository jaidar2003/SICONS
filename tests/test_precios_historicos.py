from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.application.historical_prices import crear_precio_historico
from app.modules.pricing.interfaces.schemas import PrecioHistoricoCreate


class FakeDb:
    def __init__(self, *, material, presentacion, fuente) -> None:
        self.material = material
        self.presentacion = presentacion
        self.fuente = fuente
        self.added = None

    def get(self, model, item_id):
        if model is Material and item_id == self.material.id:
            return self.material
        if model is Presentacion and item_id == self.presentacion.id:
            return self.presentacion
        if model is Fuente and item_id == self.fuente.id:
            return self.fuente
        return None

    def add(self, value) -> None:
        self.added = value

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def refresh(self, value) -> None:
        value.id = 1


def test_crear_precio_historico_normaliza_segun_presentacion() -> None:
    db = FakeDb(
        material=SimpleNamespace(id=1),
        presentacion=SimpleNamespace(id=10, material_id=1, cantidad_base=Decimal("25")),
        fuente=SimpleNamespace(id=3),
    )
    payload = PrecioHistoricoCreate(
        material_id=1,
        presentacion_id=10,
        fuente_id=3,
        fecha=date(2026, 4, 20),
        precio_original=Decimal("6250.00"),
        numero_comprobante="A-0001",
    )

    precio = crear_precio_historico(db, **payload.model_dump())

    assert precio.precio_original == Decimal("6250.00")
    assert precio.precio_normalizado == Decimal("250.0000")
    assert db.added is precio


def test_crear_precio_historico_rechaza_presentacion_de_otro_material() -> None:
    db = FakeDb(
        material=SimpleNamespace(id=1),
        presentacion=SimpleNamespace(id=10, material_id=2, cantidad_base=Decimal("25")),
        fuente=SimpleNamespace(id=3),
    )
    payload = PrecioHistoricoCreate(
        material_id=1,
        presentacion_id=10,
        fuente_id=3,
        fecha=date(2026, 4, 20),
        precio_original=Decimal("6250.00"),
    )

    with pytest.raises(HTTPException) as exc:
        crear_precio_historico(db, **payload.model_dump())

    assert exc.value.status_code == 422
    assert exc.value.detail == "La presentacion no pertenece al material"


def test_crear_precio_historico_rechaza_fecha_futura() -> None:
    db = FakeDb(
        material=SimpleNamespace(id=1),
        presentacion=SimpleNamespace(id=10, material_id=1, cantidad_base=Decimal("25")),
        fuente=SimpleNamespace(id=3),
    )
    payload = PrecioHistoricoCreate(
        material_id=1,
        presentacion_id=10,
        fuente_id=3,
        fecha=date.today() + timedelta(days=1),
        precio_original=Decimal("6250.00"),
    )

    with pytest.raises(HTTPException) as exc:
        crear_precio_historico(db, **payload.model_dump())

    assert exc.value.status_code == 422
    assert exc.value.detail == "La fecha no puede ser futura"
    assert db.added is None
