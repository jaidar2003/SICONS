import json
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock

from app.modules.chat.application.operations import (
    execute_operation,
    plan_operation,
    needs_operation_plan,
    is_explicit_confirmation,
    OperationResult,
)
from app.modules.pricing.application.purchase_optimization import PurchaseOptimizationInputItem

@pytest.fixture
def mock_material_repo():
    repo = MagicMock()
    material = MagicMock()
    material.id = 1
    material.nombre = "Cemento"
    material.unidad_base = "kg"
    repo.get_by_id.side_effect = lambda id_val: material if id_val == 1 else None
    return repo

@pytest.fixture
def mock_pricing_repo():
    repo = MagicMock()
    return repo

@pytest.fixture
def admin_user():
    user = MagicMock()
    user.id = 1
    user.rol = "admin"
    user.username = "admin"
    return user

@pytest.fixture
def regular_user():
    user = MagicMock()
    user.id = 2
    user.rol = "cliente"
    user.username = "cliente"
    return user

def test_needs_operation_plan():
    assert needs_operation_plan("Comparar estrategias para cemento") is True
    assert needs_operation_plan("Hola como estas") is False
    assert needs_operation_plan("Registrar precio") is True
    assert needs_operation_plan("confirmar") is True

def test_is_explicit_confirmation():
    assert is_explicit_confirmation("Si, confirmo la operacion") is True
    assert is_explicit_confirmation("Confirmo") is True
    assert is_explicit_confirmation("No estoy seguro") is False

def test_plan_operation_none_if_no_json(monkeypatch):
    client = MagicMock()
    client.complete.return_value = "No hay json aqui"
    plan = plan_operation("hola", client, materials=[], selected_material_id=None, horizon=3)
    assert plan["action"] == "NONE"

def test_execute_operation_admin_actions_restricted(regular_user):
    plan = {"action": "LIST_USERS"}
    with pytest.raises(ValueError, match="solamente para usuarios administradores"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=None, pricing_repo=None, current_user=regular_user)

def test_execute_operation_list_users(admin_user):
    db = MagicMock()
    user = MagicMock()
    user.id = 1
    user.username = "admin"
    user.rol = "admin"
    user.activo = True
    
    with MagicMock() as mock_list:
        import app.modules.chat.application.operations as ops
        monkeypatch_list = MagicMock(return_value=[user])
        from app.modules.auth.application.service import listar_usuarios_registrados
        # Need to monkeypatch the import inside operations.py or use a more direct way
        # Actually it's easier to just mock the function in the module
        ops.listar_usuarios_registrados = monkeypatch_list
        
        result = execute_operation({"action": "LIST_USERS"}, fallback_material=None, fallback_horizon=3, 
                                   material_repo=None, pricing_repo=None, db=db, current_user=admin_user)
        assert "USUARIOS REGISTRADOS" in result.context
        assert "admin" in result.context

def test_execute_operation_create_price_pending(admin_user):
    plan = {"action": "CREATE_PRICE", "material_id": 1, "precio": 100, "fecha": "2024-01-01"}
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=None, pricing_repo=None, db=MagicMock(), current_user=admin_user, confirmed=False)
    assert "PENDIENTE DE CONFIRMACION" in result.context

def test_execute_operation_create_price_executed(admin_user, mock_material_repo):
    db = MagicMock()
    plan = {"action": "CREATE_PRICE", "material_id": 1, "precio": 100, "fecha": "2024-01-01", "presentacion_id": None, "fuente_id": None}
    
    import app.modules.chat.application.operations as ops
    saved_mock = MagicMock()
    saved_mock.id = 99
    ops.crear_precio_historico = MagicMock(return_value=saved_mock)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=mock_material_repo, pricing_repo=None, db=db, current_user=admin_user, confirmed=True)
    assert "EJECUTADA" in result.context
    assert "ID 99" in result.context

def test_execute_operation_price_history(mock_material_repo, mock_pricing_repo):
    plan = {"action": "PRICE_HISTORY", "material_id": 1}
    price = MagicMock()
    price.fecha = date(2024, 1, 1)
    price.precio_normalizado = Decimal("100.00")
    mock_pricing_repo.get_historical_prices.return_value = [price]
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=mock_material_repo, pricing_repo=mock_pricing_repo)
    assert "RESULTADO DE HISTORIAL" in result.context
    assert "Cemento" in result.context

def test_execute_operation_simulate_scenarios(mock_material_repo, mock_pricing_repo):
    plan = {"action": "SIMULATE_SCENARIOS", "material_id": 1, "cantidad": 100, "horizontes_meses": [3, 6]}
    
    import app.modules.chat.application.operations as ops
    strat_result = MagicMock()
    strat_result.horizonte_meses = 3
    strat_result.precio_actual = 100
    strat_result.precio_proyectado_horizonte = 120
    strat_result.variacion_esperada_pct = 20
    strat_result.mejor_estrategia = "COMPRAR_AHORA"
    strat_result.ahorro_estimado = 2000
    strat_result.confiabilidad = "alta"
    
    ops.comparar_estrategias_compra = MagicMock(return_value=strat_result)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=mock_material_repo, pricing_repo=mock_pricing_repo)
    assert "RESULTADO DE ESTRATEGIAS" in result.context
    assert "Horizonte 3 meses" in result.context

def test_execute_operation_prioritize_materials(mock_material_repo, mock_pricing_repo):
    plan = {
        "action": "PRIORITIZE_MATERIALS",
        "items": [{"material_id": 1, "cantidad": 100}]
    }
    
    import app.modules.chat.application.operations as ops
    prio_result = MagicMock()
    item = MagicMock()
    item.material_nombre = "Cemento"
    item.nivel_criticidad = "ALTA"
    item.impacto_absoluto = 5000
    item.variacion_esperada_porcentual = 15
    prio_result.materiales = [item]
    
    ops.priorizar_materiales_desde_forecast = MagicMock(return_value=prio_result)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=mock_material_repo, pricing_repo=mock_pricing_repo)
    assert "RESULTADO DE CRITICIDAD" in result.context
    assert "Cemento" in result.context

def test_execute_operation_operational_recommendation(mock_material_repo, mock_pricing_repo):
    plan = {
        "action": "OPERATIONAL_RECOMMENDATION",
        "presupuesto": 10000,
        "items": [{"material_id": 1, "cantidad": 100}]
    }
    
    import app.modules.chat.application.operations as ops
    oper_result = MagicMock()
    oper_result.decision_resumen = "Comprar ahora"
    oper_result.presupuesto_total = 10000
    oper_result.presupuesto_utilizado = 8000
    oper_result.presupuesto_restante = 2000
    oper_result.ahorro_total_estimado = 1500
    item = MagicMock()
    item.material_key = "cemento-kg"
    item.accion_recomendada = "COMPRAR_AHORA"
    item.cantidad_comprar_ahora = 100
    item.cantidad_postergar = 0
    item.confianza = "alta"
    oper_result.items = [item]
    
    ops.generar_recomendacion_operativa_compra = MagicMock(return_value=oper_result)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=mock_material_repo, pricing_repo=mock_pricing_repo)
    assert "RESULTADO DE DECISION FINAL" in result.context
    assert "cemento-kg" in result.context

def test_execute_operation_admin_create_margin(admin_user):
    plan = {"action": "CREATE_MARGIN", "margen_pct": 10, "scope": "GLOBAL"}
    import app.modules.chat.application.operations as ops
    margin_mock = MagicMock()
    margin_mock.id = 5
    ops.crear_margen_comercial = MagicMock(return_value=margin_mock)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=None, pricing_repo=None, db=MagicMock(), current_user=admin_user, confirmed=True)
    assert "ID 5 creado" in result.context

def test_execute_operation_admin_update_margin(admin_user):
    plan = {"action": "UPDATE_MARGIN", "margin_id": 5, "margen_pct": 15}
    import app.modules.chat.application.operations as ops
    margin_mock = MagicMock()
    margin_mock.id = 5
    ops.actualizar_margen_comercial = MagicMock(return_value=margin_mock)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=None, pricing_repo=None, db=MagicMock(), current_user=admin_user, confirmed=True)
    assert "ID 5 actualizado" in result.context

def test_execute_operation_admin_activate_user(admin_user):
    plan = {"action": "ACTIVATE_USER", "user_id": 2}
    import app.modules.chat.application.operations as ops
    user_mock = MagicMock()
    user_mock.username = "testuser"
    ops.habilitar_usuario = MagicMock(return_value=user_mock)
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=None, pricing_repo=None, db=MagicMock(), current_user=admin_user, confirmed=True)
    assert "testuser habilitado" in result.context

def test_execute_operation_admin_delete_user(admin_user):
    plan = {"action": "DELETE_USER", "user_id": 2}
    import app.modules.chat.application.operations as ops
    ops.eliminar_usuario = MagicMock()
    
    result = execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=None, pricing_repo=None, db=MagicMock(), current_user=admin_user, confirmed=True)
    assert "usuario eliminado" in result.context

def test_execute_operation_errors(mock_material_repo):
    # Invalid quantity
    plan = {"action": "COMPARE_STRATEGIES", "material_id": 1, "cantidad": -1}
    with pytest.raises(ValueError, match="mayor a cero"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=mock_material_repo, pricing_repo=None)

    # Missing material
    plan = {"action": "COMPARE_STRATEGIES", "material_id": 999, "cantidad": 100}
    with pytest.raises(ValueError, match="material registrado"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=mock_material_repo, pricing_repo=None)

    # Invalid budget
    plan = {"action": "OPTIMIZE_BUDGET", "presupuesto": "invalid", "items": [{"material_id": 1, "cantidad": 10}]}
    with pytest.raises(ValueError, match="Falta indicar el presupuesto"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, material_repo=mock_material_repo, pricing_repo=None)

def test_execute_operation_price_history_empty(mock_material_repo, mock_pricing_repo):
    plan = {"action": "PRICE_HISTORY", "material_id": 1}
    mock_pricing_repo.get_historical_prices.return_value = []
    with pytest.raises(ValueError, match="No hay precios historicos"):
        execute_operation(plan, fallback_material=None, fallback_horizon=3, 
                               material_repo=mock_material_repo, pricing_repo=mock_pricing_repo)
