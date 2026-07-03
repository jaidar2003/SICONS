import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.modules.auth.application.service import (
    eliminar_usuario,
    habilitar_usuario,
    listar_usuarios_registrados,
)
from app.modules.chat.application.service import ChatCompletionClient
from app.modules.pricing.application.commercial_margins import (
    actualizar_margen_comercial,
    crear_margen_comercial,
    listar_margenes_comerciales,
)
from app.modules.pricing.application.historical_prices import crear_precio_historico
from app.modules.pricing.application.priorities import priorizar_materiales_desde_forecast
from app.modules.pricing.application.purchase_optimization import (
    PurchaseOptimizationInputItem,
    generar_recomendacion_operativa_compra,
    optimizar_compra_con_presupuesto,
)
from app.modules.pricing.application.purchase_strategies import comparar_estrategias_compra
from app.modules.pricing.interfaces.schemas import MaterialCriticidadCreate

SUPPORTED_ACTIONS = {
    "COMPARE_STRATEGIES",
    "SIMULATE_SCENARIOS",
    "OPTIMIZE_BUDGET",
    "OPERATIONAL_RECOMMENDATION",
    "PRIORITIZE_MATERIALS",
    "PRICE_HISTORY",
    "LIST_USERS",
    "LIST_MARGINS",
    "CREATE_PRICE",
    "CREATE_MARGIN",
    "UPDATE_MARGIN",
    "ACTIVATE_USER",
    "DELETE_USER",
}
ADMIN_ACTIONS = {"LIST_USERS", "LIST_MARGINS", "CREATE_PRICE", "CREATE_MARGIN", "UPDATE_MARGIN", "ACTIVATE_USER", "DELETE_USER"}
WRITE_ACTIONS = {"CREATE_PRICE", "CREATE_MARGIN", "UPDATE_MARGIN", "ACTIVATE_USER", "DELETE_USER"}

USER_PLANNER_PROMPT = """Extrae una operacion de BuildWise a partir de la consulta del usuario.
Devolve exclusivamente JSON valido, sin markdown.

Acciones disponibles:
- COMPARE_STRATEGIES: comparar comprar ahora, esperar o compra parcial para un material. Requiere material_id y cantidad.
- SIMULATE_SCENARIOS: comparar horizontes para un material. Requiere material_id y cantidad; horizontes por defecto [3,6,12].
- OPTIMIZE_BUDGET: distribuir presupuesto entre materiales. Requiere presupuesto e items con material_id, cantidad y criticidad.
- OPERATIONAL_RECOMMENDATION: indicar que comprar ahora/postergar para varios materiales. Requiere presupuesto e items.
- PRIORITIZE_MATERIALS: rankear criticidad de materiales. Requiere items con material_id y cantidad.
- PRICE_HISTORY: resumir datos historicos de un material.
- NONE: no coincide con esas acciones.

Formato:
{"action":"NONE","material_id":null,"horizonte_meses":3,"cantidad":null,"porcentaje_compra_inmediata":0.5,"horizontes_meses":[3,6,12],"presupuesto":null,"items":[]}
Cada item debe tener {"material_id": 1, "cantidad": 100, "criticidad": "media"}.
Solo usa ids del catalogo provisto. Si falta un dato requerido, deja el valor null o items vacio."""

ADMIN_PLANNER_PROMPT = USER_PLANNER_PROMPT + """

Operaciones adicionales disponibles solo para administrador:
- LIST_USERS: listar usuarios y su estado. Solo admin.
- LIST_MARGINS: listar margenes comerciales. Solo admin.
- CREATE_PRICE: registrar un precio historico. Solo admin; requiere material_id, presentacion_id, fuente_id, fecha y precio.
- CREATE_MARGIN: crear margen comercial. Solo admin; requiere scope (GLOBAL o MATERIAL), material_id si aplica y margen_pct.
- UPDATE_MARGIN: editar margen por id. Solo admin; requiere margin_id y margen_pct.
- ACTIVATE_USER: habilitar un usuario por id. Solo admin.
- DELETE_USER: eliminar un usuario por id. Solo admin.
Si la consulta dice CONFIRMAR, recupera la accion administrativa y parametros que el usuario pidio en el historial."""


@dataclass(frozen=True)
class OperationResult:
    context: str
    action: str


def needs_operation_plan(question: str) -> bool:
    normalized = question.lower()
    triggers = (
        "compar",
        "estrateg",
        "simul",
        "escenario",
        "optim",
        "prioriz",
        "criticidad",
        "decision final",
        "decisión final",
        "que comprar",
        "qué comprar",
        "histori",
        "usuario",
        "usuarios",
        "margen",
        "registr",
        "carg",
        "habilit",
        "elimin",
        "confirm",
    )
    return any(trigger in normalized for trigger in triggers)


def _normalized(text: str) -> str:
    return text.lower()


def _extract_decimal_from_question(question: str, patterns: tuple[str, ...]) -> Decimal | None:
    normalized = _normalized(question).replace(",", ".")
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            try:
                return Decimal(match.group(1))
            except (InvalidOperation, TypeError, ValueError):
                return None
    return None


def _resolve_material_id_by_text(question: str, materials: list, selected_material_id: int | None) -> int | None:
    normalized = _normalized(question)
    scored = []
    for material in materials:
        tokens = [token for token in re.findall(r"[a-z0-9]+", material.nombre.lower()) if len(token) >= 4]
        score = sum(1 for token in tokens if token in normalized)
        if material.nombre.lower() in normalized:
            score += 3
        if score:
            scored.append((score, material.id))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return int(scored[0][1])
    return selected_material_id


def deterministic_operation_plan(
    question: str,
    *,
    materials: list,
    selected_material_id: int | None,
    horizon: int,
    allow_admin: bool = False,
) -> dict:
    normalized = _normalized(question)
    material_id = _resolve_material_id_by_text(question, materials, selected_material_id)
    quantity = _extract_decimal_from_question(
        question,
        (
            r"\b(\d+(?:\.\d+)?)\s*(?:kg|kilos?|unidades?|m2|m²)\b",
            r"\bcantidad\s+(\d+(?:\.\d+)?)\b",
            r"\bpara\s+(\d+(?:\.\d+)?)\b",
        ),
    )
    budget = _extract_decimal_from_question(
        question,
        (
            r"\$\s*(\d+(?:\.\d+)?)",
            r"\bars\s*(\d+(?:\.\d+)?)",
            r"\bpresupuesto\s+(?:de\s+)?(\d+(?:\.\d+)?)\b",
        ),
    )

    if allow_admin and re.search(r"\b(usuario|usuarios)\b", normalized) and re.search(r"\b(lista|listar|mostra|mostrar|ver)\b", normalized):
        return {"action": "LIST_USERS"}
    if allow_admin and re.search(r"\b(margen|margenes)\b", normalized) and re.search(r"\b(lista|listar|mostra|mostrar|ver)\b", normalized):
        return {"action": "LIST_MARGINS"}
    if re.search(r"\b(histori|precio|ultimo|ultima)\b", normalized) and material_id is not None:
        return {"action": "PRICE_HISTORY", "material_id": material_id, "horizonte_meses": horizon}
    if re.search(r"\b(simul\w*|escenario\w*)\b", normalized):
        return {
            "action": "SIMULATE_SCENARIOS",
            "material_id": material_id,
            "cantidad": quantity,
            "horizonte_meses": horizon,
            "horizontes_meses": [3, 6, 12],
        }
    if re.search(r"\b(compar\w*|estrateg\w*)\b", normalized):
        return {
            "action": "COMPARE_STRATEGIES",
            "material_id": material_id,
            "cantidad": quantity,
            "horizonte_meses": horizon,
            "porcentaje_compra_inmediata": 0.5,
        }
    if re.search(r"\b(prioriz\w*|criticidad)\b", normalized) and material_id is not None:
        return {
            "action": "PRIORITIZE_MATERIALS",
            "horizonte_meses": horizon,
            "items": [{"material_id": material_id, "cantidad": quantity, "criticidad": "media"}],
        }
    if re.search(r"\b(optim\w*|decision final|que comprar|qué comprar)\b", normalized):
        items = []
        if material_id is not None and quantity is not None:
            items.append({"material_id": material_id, "cantidad": quantity, "criticidad": "media"})
        return {
            "action": "OPTIMIZE_BUDGET" if "optim" in normalized else "OPERATIONAL_RECOMMENDATION",
            "presupuesto": budget,
            "horizonte_meses": horizon,
            "items": items,
        }
    return {"action": "NONE"}


def plan_operation(
    question: str,
    client: ChatCompletionClient,
    *,
    materials: list,
    selected_material_id: int | None,
    horizon: int,
    history: list[dict[str, str]] | None = None,
    administrative_catalog: dict | None = None,
    allow_admin: bool = False,
) -> dict:
    deterministic_plan = deterministic_operation_plan(
        question,
        materials=materials,
        selected_material_id=selected_material_id,
        horizon=horizon,
        allow_admin=allow_admin,
    )
    if deterministic_plan.get("action") != "NONE":
        return deterministic_plan

    catalog = [{"id": material.id, "nombre": material.nombre, "unidad": material.unidad_base} for material in materials]
    input_message = json.dumps(
        {
            "consulta": question,
            "material_seleccionado_id": selected_material_id,
            "horizonte_activo_meses": horizon,
            "catalogo": catalog,
            "historial": history or [],
            "catalogo_administrativo": administrative_catalog or {},
        },
        ensure_ascii=True,
    )
    planner_prompt = ADMIN_PLANNER_PROMPT if allow_admin else USER_PLANNER_PROMPT
    raw = client.complete([{"role": "system", "content": planner_prompt}, {"role": "user", "content": input_message}])
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {"action": "NONE"}
    try:
        plan = json.loads(match.group())
    except json.JSONDecodeError:
        return {"action": "NONE"}
    action = str(plan.get("action", "NONE")).upper()
    plan["action"] = action if action in SUPPORTED_ACTIONS else "NONE"
    if not allow_admin and plan["action"] in ADMIN_ACTIONS:
        plan["action"] = "NONE"
    return plan


def _decimal(value, field: str) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Falta indicar {field}.") from exc
    if decimal_value <= 0:
        raise ValueError(f"{field.capitalize()} debe ser mayor a cero.")
    return decimal_value


def _horizon(plan: dict, fallback: int) -> int:
    try:
        value = int(plan.get("horizonte_meses") or fallback)
    except (TypeError, ValueError):
        value = fallback
    return value if 1 <= value <= 12 else fallback


def _material(plan: dict, fallback_material, material_repo):
    material_id = plan.get("material_id") or getattr(fallback_material, "id", None)
    material = material_repo.get_by_id(int(material_id)) if material_id is not None else None
    if material is None:
        raise ValueError("Falta indicar un material registrado.")
    return material


def is_explicit_confirmation(question: str) -> bool:
    return bool(re.search(r"\b(confirmar|confirmo|confirmar\s+operacion)\b", question.lower()))


def _items(plan: dict, material_repo) -> list[PurchaseOptimizationInputItem]:
    items = []
    for raw_item in plan.get("items") or []:
        material_id = raw_item.get("material_id")
        if material_id is None or material_repo.get_by_id(int(material_id)) is None:
            continue
        items.append(
            PurchaseOptimizationInputItem(
                material_id=int(material_id),
                cantidad_objetivo=_decimal(raw_item.get("cantidad"), "la cantidad de cada material"),
                criticidad=str(raw_item.get("criticidad") or "media").lower()
                if str(raw_item.get("criticidad") or "media").lower() in {"alta", "media", "baja"}
                else "media",
            )
        )
    if not items:
        raise ValueError("Indicame materiales y cantidades para hacer ese calculo.")
    return items


def execute_operation(
    plan: dict,
    *,
    fallback_material,
    fallback_horizon: int,
    material_repo,
    pricing_repo,
    db=None,
    current_user=None,
    confirmed: bool = False,
) -> OperationResult:
    action = plan["action"]
    horizon = _horizon(plan, fallback_horizon)

    if action in ADMIN_ACTIONS:
        if current_user is None or getattr(current_user, "rol", None) != "admin":
            raise ValueError("Esa operacion esta disponible solamente para usuarios administradores.")
        if db is None:
            raise ValueError("No se pudo abrir una transaccion administrativa.")
        if action == "LIST_USERS":
            users = listar_usuarios_registrados(db)
            return OperationResult(
                action=action,
                context="USUARIOS REGISTRADOS EN BUILDWISE:\n"
                + "\n".join(
                    f"- ID {user.id}: {user.username}; rol {user.rol}; estado {'activo' if user.activo else 'inactivo'}."
                    for user in users
                ),
            )
        if action == "LIST_MARGINS":
            margins = listar_margenes_comerciales(db)
            return OperationResult(
                action=action,
                context="MARGENES COMERCIALES EN BUILDWISE:\n"
                + "\n".join(
                    f"- ID {margin.id}: alcance {margin.scope}; margen {margin.margen_ganancia_pct}%; "
                    f"estado {'activo' if margin.activo else 'inactivo'}."
                    for margin in margins
                ),
            )
        if not confirmed:
            return OperationResult(
                action=action,
                context=(
                    "OPERACION ADMINISTRATIVA PENDIENTE DE CONFIRMACION:\n"
                    f"- Accion solicitada: {action}.\n"
                    f"- Parametros extraidos: {json.dumps(plan, ensure_ascii=True)}.\n"
                    "- No se modifico ningun dato. Pedi confirmacion escribiendo CONFIRMAR si los parametros son correctos."
                ),
            )
        if action == "CREATE_PRICE":
            material = _material(plan, fallback_material, material_repo)
            try:
                recorded_date = date.fromisoformat(str(plan.get("fecha")))
            except ValueError as exc:
                raise ValueError("Falta una fecha valida en formato AAAA-MM-DD.") from exc
            saved = crear_precio_historico(
                db,
                material_id=material.id,
                presentacion_id=int(plan["presentacion_id"]) if plan.get("presentacion_id") else None,
                fuente_id=int(plan["fuente_id"]) if plan.get("fuente_id") else None,
                fecha=recorded_date,
                precio_original=_decimal(plan.get("precio"), "el precio"),
                moneda="ARS",
                numero_comprobante=None,
                origen_dato="REAL",
                metodo_estimacion=None,
                observaciones="Carga realizada desde chatbot BuildWise.",
                usuario_id=current_user.id,
            )
            return OperationResult(action=action, context=f"OPERACION EJECUTADA: precio historico ID {saved.id} registrado.")
        if action == "CREATE_MARGIN":
            margin = crear_margen_comercial(
                db,
                scope=str(plan.get("scope") or "GLOBAL").upper(),
                material_id=int(plan["material_id"]) if plan.get("material_id") else None,
                presentation_id=None,
                product_key=None,
                margen_ganancia_pct=_decimal(plan.get("margen_pct"), "el margen porcentual"),
                activo=True,
            )
            return OperationResult(action=action, context=f"OPERACION EJECUTADA: margen comercial ID {margin.id} creado.")
        if action == "UPDATE_MARGIN":
            margin = actualizar_margen_comercial(
                db,
                margin_id=int(plan["margin_id"]),
                update_data={"margen_ganancia_pct": _decimal(plan.get("margen_pct"), "el margen porcentual")},
            )
            return OperationResult(action=action, context=f"OPERACION EJECUTADA: margen comercial ID {margin.id} actualizado.")
        if action == "ACTIVATE_USER":
            user = habilitar_usuario(db, user_id=int(plan["user_id"]))
            return OperationResult(action=action, context=f"OPERACION EJECUTADA: usuario {user.username} habilitado.")
        eliminar_usuario(db, user_id=int(plan["user_id"]), current_user=current_user)
        return OperationResult(action=action, context="OPERACION EJECUTADA: usuario eliminado.")

    if action == "PRICE_HISTORY":
        material = _material(plan, fallback_material, material_repo)
        prices = [
            price
            for price in pricing_repo.get_historical_prices(material.id, date(2000, 1, 1))
            if price.fecha <= date.today()
        ]
        if not prices:
            raise ValueError("No hay precios historicos registrados hasta hoy para ese material.")
        latest = max(prices, key=lambda item: item.fecha)
        earliest = min(prices, key=lambda item: item.fecha)
        return OperationResult(
            action=action,
            context=(
                "RESULTADO DE HISTORIAL CALCULADO POR BUILDWISE:\n"
                f"- Material: {material.nombre}; unidad base: {material.unidad_base}.\n"
                f"- Registros disponibles: {len(prices)}.\n"
                f"- Periodo registrado: {earliest.fecha} a {latest.fecha}.\n"
                f"- Ultimo precio normalizado: ARS {latest.precio_normalizado} por {material.unidad_base}."
            ),
        )

    if action in {"COMPARE_STRATEGIES", "SIMULATE_SCENARIOS"}:
        material = _material(plan, fallback_material, material_repo)
        quantity = _decimal(plan.get("cantidad"), "la cantidad a comprar")
        share = Decimal(str(plan.get("porcentaje_compra_inmediata") or "0.50"))
        horizons = [horizon]
        if action == "SIMULATE_SCENARIOS":
            horizons = sorted(
                {int(value) for value in (plan.get("horizontes_meses") or [3, 6, 12]) if 1 <= int(value) <= 12}
            )
            if len(horizons) < 2:
                raise ValueError("Indicame al menos dos horizontes entre 1 y 12 meses.")
        results = [
            comparar_estrategias_compra(
                material,
                item_horizon,
                quantity,
                pricing_repo,
                porcentaje_compra_inmediata=share,
                usar_selector_modelo=True,
            )
            for item_horizon in horizons
        ]
        lines = [
            "RESULTADO DE ESTRATEGIAS CALCULADO POR BUILDWISE:",
            f"- Material: {material.nombre}; cantidad: {quantity} {material.unidad_base}.",
        ]
        for result in results:
            fecha_base = getattr(result, "fecha_base_observada", None)
            fecha_base_text = f" observado el {fecha_base}" if fecha_base is not None else ""
            lines.extend(
                [
                    f"- Horizonte {result.horizonte_meses} meses: ultimo precio real{fecha_base_text} ARS {result.precio_actual}; "
                    f"precio futuro ARS {result.precio_proyectado_horizonte}; variacion {result.variacion_esperada_pct}%.",
                    f"  Mejor estrategia: {result.mejor_estrategia}; ahorro estimado ARS {result.ahorro_estimado}; "
                    f"confiabilidad {result.confiabilidad}.",
                ]
            )
        return OperationResult(action=action, context="\n".join(lines))

    items = _items(plan, material_repo)
    if action == "PRIORITIZE_MATERIALS":
        payload = MaterialCriticidadCreate(
            horizonte_meses=horizon,
            materiales=[
                {"material_id": item.material_id, "cantidad_requerida": item.cantidad_objetivo} for item in items
            ],
        )
        result = priorizar_materiales_desde_forecast(payload, material_repo, pricing_repo)
        lines = [f"RESULTADO DE CRITICIDAD CALCULADO POR BUILDWISE A {horizon} MESES:"]
        lines.extend(
            f"- {item.material_nombre}: nivel {item.nivel_criticidad}; impacto ARS {item.impacto_absoluto}; "
            f"variacion {item.variacion_esperada_porcentual}%."
            for item in result.materiales
        )
        return OperationResult(action=action, context="\n".join(lines))

    budget = _decimal(plan.get("presupuesto"), "el presupuesto total")
    kwargs = {
        "presupuesto_total": budget,
        "horizonte_meses": horizon,
        "materiales": items,
        "material_repo": material_repo,
        "pricing_repo": pricing_repo,
        "usar_selector_modelo": True,
    }
    if action == "OPTIMIZE_BUDGET":
        result = optimizar_compra_con_presupuesto(**kwargs)
        lines = [
            "RESULTADO DE OPTIMIZACION CALCULADO POR BUILDWISE:",
            f"- Fecha base del calculo: {getattr(result, 'fecha_base_calculo', None) or 'no disponible'}; no se usa la fecha calendario de hoy como base.",
            f"- Presupuesto total: ARS {result.presupuesto_total}; utilizado: ARS {result.presupuesto_utilizado}; "
            f"restante: ARS {result.presupuesto_restante}; ahorro estimado: ARS {result.ahorro_total_estimado}.",
        ]
        lines.extend(
            f"- {item.material_key}: {item.accion_recomendada}; comprar ahora {item.cantidad_recomendada_comprar_ahora}; "
            f"postergar {item.cantidad_recomendada_postergar}."
            for item in result.items
        )
    else:
        result = generar_recomendacion_operativa_compra(**kwargs)
        lines = [
            "RESULTADO DE DECISION FINAL CALCULADO POR BUILDWISE:",
            f"- Fecha base del calculo: {result.fecha_calculo}; corresponde al ultimo precio real observado disponible.",
            f"- {result.decision_resumen}",
            f"- Presupuesto: ARS {result.presupuesto_total}; utilizado ahora: ARS {result.presupuesto_utilizado}; "
            f"restante: ARS {result.presupuesto_restante}; ahorro estimado: ARS {result.ahorro_total_estimado}.",
        ]
        lines.extend(
            f"- {item.material_key}: {item.accion_recomendada}; comprar ahora {item.cantidad_comprar_ahora}; "
            f"postergar {item.cantidad_postergar}; confianza {item.confianza}."
            for item in result.items
        )
    return OperationResult(action=action, context="\n".join(lines))
