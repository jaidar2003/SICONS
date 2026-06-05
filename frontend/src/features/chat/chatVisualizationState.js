export const INSUFFICIENT_CHART_DATA_MESSAGE = "No hay datos suficientes en BuildWise para graficar este material.";

export function hasVisualizationData({ serie = [], forecast = null } = {}) {
  return serie.length > 0 || (forecast?.puntos || []).length > 0;
}

export function shouldShowInsufficientChartDataMessage({ loading = false, error = "", serie = [], forecast = null } = {}) {
  return !loading && !error && !hasVisualizationData({ serie, forecast });
}
