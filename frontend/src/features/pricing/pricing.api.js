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

export function createPrecioHistorico(payload, token) {
  return apiPost("/precios-historicos", payload, token);
}
