from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal


MATERIAL_KEY_CEMENTO_PORTLAND = "cemento-portland"
MATERIAL_KEY_PASTINA = "pastina"
MATERIAL_KEY_MEMBRANA_MEGAFLEX = "membrana-megaflex"

ORIGEN_DECISION_MATERIAL_HORIZONTE = "material_horizonte"
ORIGEN_DECISION_MATERIAL_DEFAULT = "material_default"
ORIGEN_DECISION_GLOBAL_FALLBACK = "global_fallback"

CONFIABILIDAD_ALTA = "alta"
CONFIABILIDAD_MEDIA = "media"
CONFIABILIDAD_MEDIA_BAJA = "media-baja"
CONFIABILIDAD_NO_CALIBRADA = "no_calibrada"


@dataclass(frozen=True)
class ForecastModelSelection:
    material_key: str
    horizonte_meses: int
    modelo: str
    regresores: tuple[str, ...]
    mape: Decimal | None
    mae: Decimal | None
    folds: int | None
    confiabilidad: str
    origen_decision: str
    justificacion: str
    no_calibrado: bool


_SELECCIONES_EXACTAS: dict[tuple[str, int], ForecastModelSelection] = {
    (MATERIAL_KEY_CEMENTO_PORTLAND, 3): ForecastModelSelection(
        material_key=MATERIAL_KEY_CEMENTO_PORTLAND,
        horizonte_meses=3,
        modelo="prophet_ipim_nivel_general",
        regresores=("ipim_nivel_general",),
        mape=Decimal("4.98"),
        mae=Decimal("6.76"),
        folds=9,
        confiabilidad=CONFIABILIDAD_ALTA,
        origen_decision=ORIGEN_DECISION_MATERIAL_HORIZONTE,
        justificacion=(
            "Configuracion recomendada para Cemento Portland a 3 meses segun benchmark "
            "documentado, con MAPE minimo medido y coherencia economica del regresor."
        ),
        no_calibrado=False,
    ),
    (MATERIAL_KEY_PASTINA, 3): ForecastModelSelection(
        material_key=MATERIAL_KEY_PASTINA,
        horizonte_meses=3,
        modelo="prophet_blue_ipc",
        regresores=("dolar_blue", "ipc"),
        mape=Decimal("5.00"),
        mae=Decimal("120.90"),
        folds=9,
        confiabilidad=CONFIABILIDAD_MEDIA,
        origen_decision=ORIGEN_DECISION_MATERIAL_HORIZONTE,
        justificacion=(
            "Configuracion recomendada para Pastina a 3 meses segun benchmark documentado, "
            "con mejor desempeno relativo medido para este material."
        ),
        no_calibrado=False,
    ),
    (MATERIAL_KEY_MEMBRANA_MEGAFLEX, 3): ForecastModelSelection(
        material_key=MATERIAL_KEY_MEMBRANA_MEGAFLEX,
        horizonte_meses=3,
        modelo="prophet_ipc",
        regresores=("ipc",),
        mape=Decimal("8.31"),
        mae=Decimal("734.37"),
        folds=9,
        confiabilidad=CONFIABILIDAD_MEDIA_BAJA,
        origen_decision=ORIGEN_DECISION_MATERIAL_HORIZONTE,
        justificacion=(
            "Configuracion recomendada para Membrana Megaflex a 3 meses segun benchmark "
            "documentado, priorizando el mejor MAPE disponible para la serie actual."
        ),
        no_calibrado=False,
    ),
}

_SELECCIONES_POR_MATERIAL: dict[str, ForecastModelSelection] = {
    material_key: selection for (material_key, _horizonte), selection in _SELECCIONES_EXACTAS.items()
}

_FALLBACK_GLOBAL = ForecastModelSelection(
    material_key="unknown",
    horizonte_meses=0,
    modelo="prophet_base",
    regresores=(),
    mape=None,
    mae=None,
    folds=None,
    confiabilidad=CONFIABILIDAD_NO_CALIBRADA,
    origen_decision=ORIGEN_DECISION_GLOBAL_FALLBACK,
    justificacion=(
        "Se aplica prophet_base sin regresores como fallback operativo porque no existe "
        "una calibracion documentada para el material solicitado."
    ),
    no_calibrado=True,
)


def resolve_model_selection(material_key: str, horizonte_meses: int) -> ForecastModelSelection:
    exacta = _SELECCIONES_EXACTAS.get((material_key, horizonte_meses))
    if exacta is not None:
        return exacta

    por_material = _SELECCIONES_POR_MATERIAL.get(material_key)
    if por_material is not None:
        return replace(
            por_material,
            material_key=material_key,
            horizonte_meses=horizonte_meses,
            origen_decision=ORIGEN_DECISION_MATERIAL_DEFAULT,
            justificacion=(
                "Se reutiliza la mejor configuracion documentada para este material porque "
                f"no existe una calibracion exacta para horizonte de {horizonte_meses} meses."
            ),
            no_calibrado=True,
        )

    return replace(
        _FALLBACK_GLOBAL,
        material_key=material_key,
        horizonte_meses=horizonte_meses,
    )
