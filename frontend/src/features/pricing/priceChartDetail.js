function asFinitePrice(value) {
  if (value === null || value === undefined || value === "") return null;
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

export function getChartPointOrigin(origins = []) {
  const hasObserved = origins.includes("REAL");
  const hasEstimated = origins.includes("ESTIMADO");

  if (hasObserved && hasEstimated) return { label: "Observado y estimado", color: "warning" };
  if (hasEstimated) return { label: "Estimado", color: "warning" };
  if (hasObserved) return { label: "Observado", color: "success" };
  return { label: "Sin clasificar", color: "default" };
}

export function buildComparativeChartPoints({
  serie,
  forecastPoints,
  historicalCostPrices,
  historicalRetailPrices,
  forecastCostPrices,
  forecastRetailPrices,
}) {
  return [
    ...serie.map((point, index) => ({
      key: `historical-${point.fecha}-${index}`,
      date: point.fecha,
      costPrice: asFinitePrice(historicalCostPrices[index]),
      retailPrice: asFinitePrice(historicalRetailPrices[index]),
      origin: getChartPointOrigin(point.origenes_dato),
      isForecast: false,
    })),
    ...forecastPoints.map((point, index) => ({
      key: `forecast-${point.fecha}-${index}`,
      date: point.fecha,
      costPrice: asFinitePrice(forecastCostPrices[index]),
      retailPrice: asFinitePrice(forecastRetailPrices[index]),
      origin: { label: "Estimado", color: "warning" },
      isForecast: true,
    })),
  ].sort((left, right) => String(left.date).localeCompare(String(right.date)));
}
