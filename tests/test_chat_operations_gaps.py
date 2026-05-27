from unittest.mock import MagicMock

import pytest

from app.modules.chat.application.operations import (
    _decimal,
    _items,
    _material,
    execute_operation,
    is_explicit_confirmation,
    plan_operation,
)


def test_plan_operation_json_error():
    client = MagicMock()
    # Return invalid JSON
    client.complete.return_value = "invalid { json"
    plan = plan_operation("hola", client, materials=[], selected_material_id=None, horizon=3)
    assert plan["action"] == "NONE"

def test_decimal_error_negative():
    with pytest.raises(ValueError, match="debe ser mayor a cero"):
        _decimal("-10", "valor")

def test_material_not_found():
    repo = MagicMock()
    repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="Falta indicar un material registrado"):
        _material({"material_id": 999}, None, repo)

def test_is_explicit_confirmation():
    assert is_explicit_confirmation("Por favor confirmar operacion") is True
    assert is_explicit_confirmation("Solo una pregunta") is False

def test_items_empty():
    repo = MagicMock()
    with pytest.raises(ValueError, match="Indicame materiales y cantidades"):
        _items({"items": []}, repo)

def test_execute_operation_admin_required():
    plan = {"action": "LIST_USERS"}
    with pytest.raises(ValueError, match="disponible solamente para usuarios administradores"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=None, pricing_repo=None)

def test_execute_operation_no_db():
    plan = {"action": "LIST_USERS"}
    user = MagicMock(rol="admin")
    with pytest.raises(ValueError, match="No se pudo abrir una transaccion administrativa"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=None, pricing_repo=None, current_user=user)

def test_execute_operation_admin_not_confirmed():
    plan = {"action": "ACTIVATE_USER", "user_id": 1}
    user = MagicMock(rol="admin")
    db = MagicMock()
    res = execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=None, pricing_repo=None, db=db, current_user=user, confirmed=False)
    assert "PENDIENTE DE CONFIRMACION" in res.context

def test_execute_operation_price_history_empty():
    material = MagicMock(id=1, nombre="M1")
    repo = MagicMock()
    repo.get_historical_prices.return_value = []
    plan = {"action": "PRICE_HISTORY", "material_id": 1}
    material_repo = MagicMock()
    material_repo.get_by_id.return_value = material
    with pytest.raises(ValueError, match="No hay precios historicos registrados"):
        execute_operation(plan, fallback_material=material, fallback_horizon=3, material_repo=material_repo, pricing_repo=repo)

def test_execute_operation_simulate_scenarios_insufficient_horizons():
    material = MagicMock(id=1, nombre="M1", unidad_base="kg")
    material_repo = MagicMock()
    material_repo.get_by_id.return_value = material
    plan = {"action": "SIMULATE_SCENARIOS", "material_id": 1, "cantidad": 100, "horizontes_meses": [3]}
    with pytest.raises(ValueError, match="al menos dos horizontes"):
        execute_operation(plan, fallback_material=material, fallback_horizon=3, material_repo=material_repo, pricing_repo=None)

def test_execute_operation_delete_user(monkeypatch):
    plan = {"action": "DELETE_USER", "user_id": 2}
    user = MagicMock(id=1, rol="admin")
    db = MagicMock()
    
    mock_delete = MagicMock()
    monkeypatch.setattr("app.modules.chat.application.operations.eliminar_usuario", mock_delete)
    
    res = execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=None, pricing_repo=None, db=db, current_user=user, confirmed=True)
    assert "usuario eliminado" in res.context.lower()
    mock_delete.assert_called_once()
