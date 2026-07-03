import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Presentacion
from app.modules.chat.application.context import resolve_horizon
from app.modules.pricing.infrastructure.models import CommercialMargin, ExternalIndexValue, PrecioHistorico

BACKEND_CONTEXT_HEADER = (
    "CONTEXTO RECUPERADO DE BUILDWISE. Estos datos provienen del backend y prevalecen "
    "sobre conocimiento general del modelo:"
)
MATERIAL_ALIASES = {
    "cemento portland": {"cemento", "portland", "cemnto", "cemento loma negra", "bolsa cemento", "bolsas cemento"},
    "pastina": {"pastina", "pastina klaukol", "klaukol", "pastina blanca"},
    "membrana megaflex": {"membrana", "megaflex", "membrana asfaltica", "membrana asfáltica", "impermeabilizante"},
}
CHAT_INTENTS = {"HISTORICO", "FORECAST", "RECOMENDACION", "PRESUPUESTO", "CATALOGO", "ADMIN", "FUERA_ALCANCE"}


@dataclass(frozen=True)
class BackendRetrievalResult:
    context: str | None
    material: object | None
    horizon: int
    sources: tuple[str, ...] = ()
    source_evidence: tuple[dict, ...] = ()
    material_resolution_source: str | None = None


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _normalized(text)))


def _alias_score(question: str, material_name: str) -> int:
    normalized_question = _normalized(question)
    normalized_material = _normalized(material_name)
    aliases = MATERIAL_ALIASES.get(normalized_material, set())
    score = 0
    for alias in aliases:
        normalized_alias = _normalized(alias)
        if re.search(rf"\b{re.escape(normalized_alias)}\b", normalized_question):
            score = max(score, len(_tokens(normalized_alias)) + 3)
    return score


def _wants_catalog(question: str) -> bool:
    normalized = _normalized(question)
    return bool(re.search(r"\b(materiales|catalogo|catalogo|productos|presentaciones|fuentes)\b", normalized))


def _wants_history(question: str) -> bool:
    normalized = _normalized(question)
    return bool(re.search(r"\b(precio|precios|historico|historial|serie|ultimo|ultima|fuente|factura|evolucion|evoluciono)\b", normalized))


def _wants_forecast_or_decision(question: str) -> bool:
    normalized = _normalized(question)
    return bool(
        re.search(
            r"\b(forecast|proyeccion|proyectado|conviene|recomendacion|comprar|esperar|mape|mae|confiabilidad|decision)\b",
            normalized,
        )
    )


def _wants_external_indices(question: str) -> bool:
    normalized = _normalized(question)
    return bool(re.search(r"\b(ipc|dolar|mayorista|blue|oficial|ipim|indice|indices|regresor|regresores)\b", normalized))


def _wants_margins(question: str) -> bool:
    return bool(re.search(r"\b(margen|margenes|precio comercial)\b", _normalized(question)))


def wants_visualization(question: str) -> bool:
    normalized = _normalized(question)
    return bool(
        re.search(
            r"\b(mostra|mostrar|mostrame|ver|visualiza|visualizar|grafica|graficar|graficame|grafico|graficos|chart|evolucion|curva)\b",
            normalized,
        )
    )


def suggest_visualization(question: str, *, intent: str | None, material: object | None, horizon: int) -> dict | None:
    if material is None or not wants_visualization(question):
        return None
    material_id = getattr(material, "id", None)
    if material_id is None:
        return None

    normalized = _normalized(question)
    asks_forecast = intent in {"FORECAST", "RECOMENDACION"} or _wants_forecast_or_decision(question)
    asks_history = intent == "HISTORICO" or _wants_history(question)
    if asks_forecast and asks_history:
        visualization_type = "PRICE_HISTORY_FORECAST"
    elif asks_forecast or re.search(r"\b(forecast|proyeccion|proyectado)\b", normalized):
        visualization_type = "FORECAST"
    else:
        visualization_type = "PRICE_HISTORY"

    return {
        "tipo": visualization_type,
        "material_id": int(material_id),
        "horizonte_meses": horizon if visualization_type in {"FORECAST", "PRICE_HISTORY_FORECAST"} else None,
    }


def classify_chat_intent(question: str, *, accepted_scope: bool = True, admin_only: bool = False) -> str:
    if not accepted_scope:
        return "FUERA_ALCANCE"
    normalized = _normalized(question)
    if admin_only or re.search(
        r"\b(usuario|usuarios|margen|margenes|registrar|cargar|crear|actualizar|modificar|habilitar|eliminar|borrar)\b",
        normalized,
    ):
        return "ADMIN"
    if re.search(r"\b(presupuesto|cotizar|cotizacion|propuesta|necesito comprar|necesito\s+\d+|obra)\b", normalized):
        return "PRESUPUESTO"
    if re.search(r"\b(estrategia|estrategias|optimizar|priorizar|criticidad|conviene|recomendacion|comprar|esperar|decision)\b", normalized):
        return "RECOMENDACION"
    if re.search(r"\b(forecast|proyeccion|proyectado|mape|mae|confiabilidad|modelo|anomalia|anomalias)\b", normalized):
        return "FORECAST"
    if _wants_history(question):
        return "HISTORICO"
    if _wants_catalog(question) or _wants_external_indices(question):
        return "CATALOGO"
    return "CATALOGO"


def resolve_material_from_question_with_source(question: str, material_repo, selected_material_id: int | None = None):
    if hasattr(material_repo, "list_active"):
        question_tokens = _tokens(question)
        candidates = []
        for material in material_repo.list_active():
            name_tokens = _tokens(material.nombre)
            if not name_tokens:
                continue
            overlap = len(question_tokens & name_tokens)
            overlap += _alias_score(question, material.nombre)
            normalized_name = _normalized(material.nombre)
            normalized_question = _normalized(question)
            if normalized_name in normalized_question:
                overlap += len(name_tokens) + 2
            if overlap:
                candidates.append((overlap, material))
        if candidates:
            candidates.sort(key=lambda item: (-item[0], item[1].id))
            return candidates[0][1], "pregunta"

    if selected_material_id is not None:
        material = material_repo.get_by_id(selected_material_id)
        if material is not None:
            return material, "contexto"
    return None, None


def resolve_material_from_question(question: str, material_repo, selected_material_id: int | None = None):
    material, _source = resolve_material_from_question_with_source(question, material_repo, selected_material_id)
    return material


def _format_decimal(value) -> str:
    if isinstance(value, Decimal):
        return str(value.normalize())
    return str(value)


def _source_priority(price) -> int:
    source_name = _normalized(price.fuente.nombre) if getattr(price, "fuente", None) is not None else ""
    if "factura" in source_name:
        return 2
    if "canonico" in source_name or "canonico" in source_name:
        return 0
    return 1


def _catalog_context(materials: list, db: Session) -> list[str]:
    lines = ["FUENTE catalogo.materiales:"]
    lines.append(f"- Materiales activos disponibles: {len(materials)}.")
    for material in materials[:8]:
        lines.append(f"- ID {material.id}: {material.nombre}; unidad base {material.unidad_base}.")
    if len(materials) > 8:
        lines.append(f"- Hay {len(materials) - 8} materiales activos adicionales no listados en este contexto.")

    presentations = list(
        db.scalars(
            select(Presentacion)
            .where(Presentacion.activa.is_(True))
            .order_by(Presentacion.material_id.asc(), Presentacion.id.asc())
            .limit(12)
        )
    )
    if presentations:
        lines.append("FUENTE catalogo.presentaciones:")
        for presentation in presentations:
            lines.append(
                f"- ID {presentation.id}; material_id {presentation.material_id}; "
                f"{presentation.nombre_presentacion}; {presentation.cantidad_base} {presentation.unidad_presentacion}."
            )
    return lines


def _material_catalog_context(material, db: Session) -> list[str]:
    lines = ["FUENTE catalogo.materiales:"]
    material_id = getattr(material, "id", None)
    lines.append(f"- Material resuelto: ID {material_id or 'sin id'}; {material.nombre}; unidad base {material.unidad_base}.")
    if getattr(material, "categoria", None):
        lines.append(f"- Categoria: {material.categoria}.")
    if getattr(material, "marca", None):
        lines.append(f"- Marca: {material.marca}.")
    if getattr(material, "descripcion", None):
        lines.append(f"- Descripcion: {material.descripcion}.")

    presentations = (
        list(
            db.scalars(
                select(Presentacion)
                .where(Presentacion.material_id == material_id, Presentacion.activa.is_(True))
                .order_by(Presentacion.id.asc())
            )
        )
        if material_id is not None
        else []
    )
    if presentations:
        lines.append("FUENTE catalogo.presentaciones:")
        for presentation in presentations:
            lines.append(
                f"- ID {presentation.id}: {presentation.nombre_presentacion}; "
                f"{presentation.cantidad_base} {presentation.unidad_presentacion}."
            )
    return lines


def _history_context(material, pricing_repo, db: Session) -> tuple[list[str], dict | None]:
    prices = [
        price
        for price in pricing_repo.get_historical_prices(material.id, date(2000, 1, 1))
        if price.fecha <= date.today()
    ]
    if not prices:
        return ["FUENTE precios_historicos:", "- No hay precios historicos observados hasta hoy para este material."], {
            "source": "precios_historicos",
            "records": [],
        }

    latest = max(prices, key=lambda price: (price.fecha, _source_priority(price), price.id))
    first = min(prices, key=lambda price: (price.fecha, price.id))
    min_price = min(prices, key=lambda price: price.precio_normalizado)
    max_price = max(prices, key=lambda price: price.precio_normalizado)
    real_count = db.scalar(
        select(func.count())
        .select_from(PrecioHistorico)
        .where(
            PrecioHistorico.material_id == material.id,
            PrecioHistorico.origen_dato == "REAL",
            PrecioHistorico.fecha <= date.today(),
        )
    )
    estimated_count = db.scalar(
        select(func.count())
        .select_from(PrecioHistorico)
        .where(
            PrecioHistorico.material_id == material.id,
            PrecioHistorico.origen_dato == "ESTIMADO",
            PrecioHistorico.fecha <= date.today(),
        )
    )
    source_names = sorted({price.fuente.nombre for price in prices if getattr(price, "fuente", None) is not None})

    lines = ["FUENTE precios_historicos:"]
    lines.append(f"- Registros disponibles: {len(prices)}; reales: {real_count or 0}; estimados: {estimated_count or 0}.")
    lines.append(
        f"- Rango temporal: {first.fecha.isoformat()} a {latest.fecha.isoformat()}."
    )
    lines.append(
        f"- Ultimo precio normalizado: ARS {_format_decimal(latest.precio_normalizado)} por {material.unidad_base} "
        f"en {latest.fecha.isoformat()}; fuente {latest.fuente.nombre if latest.fuente else 'sin fuente'}."
    )
    lines.append(
        f"- Precio minimo observado: ARS {_format_decimal(min_price.precio_normalizado)} "
        f"en {min_price.fecha.isoformat()}."
    )
    lines.append(
        f"- Precio maximo observado: ARS {_format_decimal(max_price.precio_normalizado)} "
        f"en {max_price.fecha.isoformat()}."
    )
    if source_names:
        lines.append(f"- Fuentes presentes: {', '.join(source_names[:8])}.")

    recent = sorted(prices, key=lambda price: (price.fecha, _source_priority(price), price.id), reverse=True)[:5]
    lines.append("- Ultimos registros:")
    evidence_records = []
    for price in recent:
        lines.append(
            f"  - {price.fecha.isoformat()}: ARS {_format_decimal(price.precio_normalizado)} por {material.unidad_base}; "
            f"fuente {price.fuente.nombre if price.fuente else 'sin fuente'}; comprobante {price.numero_comprobante or 'sin comprobante'}."
        )
        evidence_records.append(
            {
                "fecha": price.fecha.isoformat(),
                "precio_normalizado": _format_decimal(price.precio_normalizado),
                "unidad_base": material.unidad_base,
                "fuente": price.fuente.nombre if price.fuente else None,
                "comprobante": price.numero_comprobante,
            }
        )
    return lines, {"source": "precios_historicos", "records": evidence_records}


def _external_indices_context(db: Session) -> list[str]:
    rows = list(
        db.execute(
            select(
                ExternalIndexValue.source_name,
                ExternalIndexValue.series_id,
                func.count(ExternalIndexValue.id),
                func.min(ExternalIndexValue.date),
                func.max(ExternalIndexValue.date),
            )
            .group_by(ExternalIndexValue.source_name, ExternalIndexValue.series_id)
            .order_by(ExternalIndexValue.source_name.asc(), ExternalIndexValue.series_id.asc())
            .limit(12)
        )
    )
    if not rows:
        return ["FUENTE external_index_values:", "- No hay indices externos cargados."]
    lines = ["FUENTE external_index_values:"]
    for source_name, series_id, count, min_date, max_date in rows:
        lines.append(f"- {source_name}/{series_id}: {count} registros; rango {min_date} a {max_date}.")
    return lines


def _sources_context(db: Session) -> list[str]:
    sources = list(db.scalars(select(Fuente).order_by(Fuente.id.asc()).limit(12)))
    if not sources:
        return ["FUENTE catalogo.fuentes:", "- No hay fuentes registradas."]
    lines = ["FUENTE catalogo.fuentes:"]
    for source in sources:
        lines.append(f"- ID {source.id}: {source.nombre}; tipo {source.tipo_fuente or 'sin tipo'}.")
    return lines


def _margins_context(db: Session, material_id: int | None, *, is_admin: bool) -> list[str]:
    if not is_admin:
        return ["FUENTE commercial_margins:", "- Los margenes comerciales detallados estan disponibles solo para usuarios administradores."]
    stmt = select(CommercialMargin).where(CommercialMargin.activo.is_(True)).order_by(CommercialMargin.id.asc())
    if material_id is not None:
        stmt = stmt.where((CommercialMargin.material_id == material_id) | (CommercialMargin.scope == "GLOBAL"))
    margins = list(db.scalars(stmt.limit(12)))
    if not margins:
        return ["FUENTE commercial_margins:", "- No hay margenes comerciales activos para el alcance solicitado."]
    lines = ["FUENTE commercial_margins:"]
    for margin in margins:
        lines.append(
            f"- ID {margin.id}: scope {margin.scope}; material_id {margin.material_id}; "
            f"presentation_id {margin.presentation_id}; margen {margin.margen_ganancia_pct}%."
        )
    return lines


def build_backend_retrieval_context(
    question: str,
    *,
    material_repo,
    pricing_repo,
    db: Session,
    selected_material_id: int | None = None,
    fallback_horizon: int = 3,
    is_admin: bool = False,
) -> BackendRetrievalResult:
    horizon = resolve_horizon(question, fallback_horizon)
    material, material_resolution_source = resolve_material_from_question_with_source(question, material_repo, selected_material_id)
    wants_catalog = _wants_catalog(question)
    wants_history = _wants_history(question)
    wants_forecast = _wants_forecast_or_decision(question)
    wants_indices = _wants_external_indices(question)
    wants_margins = _wants_margins(question)

    lines: list[str] = [BACKEND_CONTEXT_HEADER]
    sources: list[str] = []
    source_evidence: list[dict] = []
    retrieved_any = False

    if material is not None:
        lines.extend(_material_catalog_context(material, db))
        sources.append("catalogo.materiales")
        retrieved_any = True
        if wants_history or not wants_forecast:
            history_lines, history_evidence = _history_context(material, pricing_repo, db)
            lines.extend(history_lines)
            sources.append("precios_historicos")
            if history_evidence is not None:
                source_evidence.append(history_evidence)
        if wants_margins:
            lines.extend(_margins_context(db, getattr(material, "id", None), is_admin=is_admin))
            sources.append("commercial_margins")
    elif wants_catalog:
        materials = material_repo.list_active()
        lines.extend(_catalog_context(materials, db))
        sources.extend(("catalogo.materiales", "catalogo.presentaciones"))
        retrieved_any = True

    if wants_indices:
        lines.extend(_external_indices_context(db))
        sources.append("external_index_values")
        retrieved_any = True
    if wants_catalog and "fuente" in _normalized(question):
        lines.extend(_sources_context(db))
        sources.append("catalogo.fuentes")
        retrieved_any = True
    if wants_margins and material is None:
        lines.extend(_margins_context(db, None, is_admin=is_admin))
        sources.append("commercial_margins")
        retrieved_any = True

    if not retrieved_any:
        return BackendRetrievalResult(context=None, material=material, horizon=horizon, material_resolution_source=material_resolution_source)

    lines.append(
        "REGLA DE RESPUESTA: responde solo con los datos recuperados/calculados. "
        "Si falta un dato en el contexto, indicá exactamente qué falta en BuildWise."
    )
    unique_sources = tuple(dict.fromkeys(sources))
    return BackendRetrievalResult(
        context="\n".join(lines),
        material=material,
        horizon=horizon,
        sources=unique_sources,
        source_evidence=tuple(source_evidence),
        material_resolution_source=material_resolution_source,
    )
