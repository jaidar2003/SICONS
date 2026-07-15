const BACKEND_DECISION_LABELS = {
  COMPRAR_AHORA: "Comprar ahora",
  ESPERAR: "Esperar",
  MONITOREAR: "Monitorear",
  POSTERGAR: "Postergar",
  ESCALONAR: "Comprar por etapas",
  SIN_VENTAJA_CLARA: "Sin ventaja clara",
};

export function getForecastTrend(forecast) {
  const current = Number(forecast?.ultimo_precio_observado);
  const projected = Number(forecast?.puntos?.[0]?.precio_proyectado);
  if (!Number.isFinite(current) || current <= 0 || !Number.isFinite(projected)) {
    return {
      deltaPct: null,
      label: "Sin proyección disponible",
      description: "No hay datos suficientes para describir una tendencia.",
    };
  }

  const deltaPct = ((projected - current) / current) * 100;
  const direction = deltaPct > 0 ? "aumento" : deltaPct < 0 ? "disminución" : "estabilidad";
  return {
    deltaPct,
    label: deltaPct > 0 ? "Tendencia alcista" : deltaPct < 0 ? "Tendencia bajista" : "Tendencia estable",
    description: `El precio proyectado presenta una ${direction} para el primer mes del horizonte seleccionado.`,
  };
}

export function getSummaryDecisionPresentation({ recommendation = null, forecast = null } = {}) {
  if (recommendation?.decision) {
    return {
      kind: "backend-recommendation",
      eyebrow: "Recomendación de compra",
      title: BACKEND_DECISION_LABELS[recommendation.decision] || recommendation.decision,
      description: recommendation.justificacion || "Resultado calculado por el motor de decisión de BuildWise.",
      provenance: "Resultado del motor de decisión",
    };
  }

  const trend = getForecastTrend(forecast);
  return {
    kind: "trend",
    eyebrow: "Tendencia esperada",
    title: trend.label,
    description: trend.description,
    provenance: "Esta tendencia no constituye por sí sola una recomendación de compra.",
  };
}
