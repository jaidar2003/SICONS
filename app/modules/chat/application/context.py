import re
import unicodedata
from decimal import Decimal

from app.modules.pricing.application.purchase_recommendations import recomendar_momento_compra


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")


def resolve_horizon(question: str, fallback_horizon: int) -> int:
    match = re.search(r"\b(\d{1,2})\s*mes(?:es)?\b", _normalized(question))
    if match:
        horizon = int(match.group(1))
        if 1 <= horizon <= 12:
            return horizon
    return fallback_horizon


def build_material_context(material, horizon: int, pricing_repo, *, is_admin: bool = False) -> str:
    recommendation = recomendar_momento_compra(
        material,
        horizon,
        "media",
        Decimal("1"),
        pricing_repo,
        usar_selector_modelo=True,
    )
    lines = [
        "CONTEXTO CALCULADO POR BUILDWISE. Esta informacion prevalece sobre supuestos generales:",
        f"- Material seleccionado: {material.nombre}. Unidad base: {material.unidad_base}.",
        f"- Horizonte analizado: {recommendation.horizonte_meses} meses.",
        "- Criticidad usada para orientar el timing: media.",
        "- La evaluacion economica es por 1 unidad base; sin una cantidad requerida no calcules costo total de obra.",
        f"- Decision del motor: {recommendation.decision}.",
        f"- Confiabilidad del forecast: {recommendation.confiabilidad}.",
        f"- Justificacion calculada: {recommendation.justificacion}",
    ]
    if recommendation.precio_actual is not None:
        lines.append(f"- Ultimo precio observado: ARS {recommendation.precio_actual} por {material.unidad_base}.")
    if recommendation.precio_proyectado_horizonte is not None:
        lines.append(
            f"- Precio proyectado al horizonte: ARS {recommendation.precio_proyectado_horizonte} por {material.unidad_base}."
        )
    if getattr(recommendation, "precio_proyectado_optimista", None) is not None:
        lines.append(f"- Escenario optimista (precio mas bajo): ARS {recommendation.precio_proyectado_optimista} por {material.unidad_base}.")
    if getattr(recommendation, "precio_proyectado_pesimista", None) is not None:
        lines.append(f"- Escenario pesimista (precio mas alto): ARS {recommendation.precio_proyectado_pesimista} por {material.unidad_base}.")
    if recommendation.variacion_esperada_pct is not None:
        lines.append(f"- Variacion esperada: {recommendation.variacion_esperada_pct}%.")
    if recommendation.mape is not None:
        lines.append(f"- MAPE del modelo: {recommendation.mape}%.")
    for warning in recommendation.advertencias:
        lines.append(f"- Advertencia: {warning}")
    lines.append(
        "- No pidas precios por zona ni acceso a reportes: ya estas respondiendo con datos internos del material seleccionado."
    )
    lines.append(
        "- Capacidades conversacionales disponibles: explicar precios/forecast/recomendacion; resumir historial; "
        "comparar estrategias; simular horizontes; priorizar materiales; optimizar presupuesto y generar decision final."
    )
    if is_admin:
        lines.append(
            "- Las operaciones administrativas sobre precios, margenes y usuarios solo pueden ejecutarse "
            "tras confirmacion explicita."
        )
    return "\n".join(lines)
