import { apiGet, apiPost } from "../../shared/api/http.js";

export function fetchPriceRange(token) {
  return apiGet("/precios-historicos/rango", token);
}

export function fetchSerie({ materialId, desde, hasta, token }) {
  const params = new URLSearchParams({ agrupacion: "mensual" });
  if (desde) params.set("desde", desde);
  if (hasta) params.set("hasta", hasta);
  return apiGet(`/materiales/${materialId}/serie-precios?${params.toString()}`, token);
}

export function fetchForecast({ materialId, horizonteMeses = 3, token }) {
  const params = new URLSearchParams({ horizonte_meses: String(horizonteMeses) });
  return apiGet(`/materiales/${materialId}/forecast?${params.toString()}`, token);
}

export function fetchCommercialPrice({ materialId, horizonteMeses = 3, token }) {
  const params = new URLSearchParams({ horizonte_meses: String(horizonteMeses) });
  return apiGet(`/materiales/${materialId}/precio-comercial?${params.toString()}`, token);
}

export function createPrecioHistorico(payload, token) {
  return apiPost("/precios-historicos", payload, token);
}

export function optimizePurchaseBudget(payload, token) {
  return apiPost("/compras/optimizar-presupuesto", payload, token);
}

export function prioritizeMaterials(payload, token) {
  return apiPost("/materiales/criticidad", payload, token);
}

export function recommendPurchase(payload, token, materialId) {
  return apiPost(`/materiales/${materialId}/recomendacion-compra`, payload, token);
}

export function comparePurchaseStrategies(payload, token, materialId) {
  return apiPost(`/materiales/${materialId}/comparacion-estrategias-compra`, payload, token);
}

export function fetchPriceVariationBetweenDates({ materialId, fechaDesde, fechaHasta, token }) {
  const params = new URLSearchParams({
    fecha_desde: fechaDesde,
    fecha_hasta: fechaHasta,
  });
  return apiGet(`/materiales/${materialId}/variacion-entre-fechas?${params.toString()}`, token);
}

export function simulatePurchaseScenarios(payload, token, materialId) {
  return apiPost(`/materiales/${materialId}/simulacion-escenarios-compra`, payload, token);
}
