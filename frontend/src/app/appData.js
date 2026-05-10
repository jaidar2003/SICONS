import dayjs from "dayjs";

import { fetchFuentes, fetchMateriales, fetchPresentaciones } from "../features/catalog/catalog.api.js";
import { fetchCommercialPrice, fetchForecast, fetchPriceRange, fetchSerie } from "../features/pricing/pricing.api.js";
import { toApiDate } from "../shared/utils/formatters.js";

export function buildComparisonRows(results) {
  return results
    .filter((result) => result.serie.length > 0)
    .map((result) => {
      const first = result.serie[0];
      const last = result.serie[result.serie.length - 1];
      const firstValue = Number(first.precio_promedio_normalizado);
      const lastValue = Number(last.precio_promedio_normalizado);
      const variation = firstValue === 0 ? 0 : ((lastValue - firstValue) / firstValue) * 100;
      const sampleSize = result.serie.reduce((total, point) => total + Number(point.cantidad_registros || 0), 0);
      return { material: result.material, first, last, firstValue, lastValue, variation, sampleSize };
    })
    .sort((left, right) => left.variation - right.variation);
}

export async function loadMaterialAnalysis({ materialId, from, to, horizon, materials, token }) {
  if (!materialId) {
    return {
      serie: [],
      forecast: null,
      commercialPrice: null,
      comparisonRows: [],
    };
  }

  const desde = toApiDate(from);
  const hasta = toApiDate(to);
  const [serie, forecast, commercialPrice, comparisonResults] = await Promise.all([
    fetchSerie({ materialId, desde, hasta, token }),
    fetchForecast({ materialId, horizonteMeses: horizon, token }).catch(() => null),
    fetchCommercialPrice({ materialId, horizonteMeses: horizon, token }).catch(() => null),
    Promise.all(
      materials.map(async (material) => ({
        material,
        serie: await fetchSerie({ materialId: material.id, desde, hasta, token }),
      }))
    ),
  ]);

  return {
    serie,
    forecast,
    commercialPrice,
    comparisonRows: buildComparisonRows(comparisonResults),
  };
}

export async function loadInitialAppData({ token, forecastHorizon, clientDefaultStart }) {
  const [materiales, presentaciones, fuentes, range] = await Promise.all([
    fetchMateriales(token),
    fetchPresentaciones(token),
    fetchFuentes(token),
    fetchPriceRange(token),
  ]);

  const defaultMaterial = materiales.find((material) => material.nombre.toLowerCase().includes("cemento")) || materiales[0];
  const selectedMaterialId = defaultMaterial ? String(defaultMaterial.id) : "";
  const rangeDesde = range.desde ? dayjs(range.desde) : null;
  const desde = rangeDesde ? (rangeDesde.isAfter(clientDefaultStart) ? rangeDesde : clientDefaultStart) : clientDefaultStart;
  const hasta = dayjs(range.hasta || range.hoy);
  const maxDate = range.hoy ? dayjs(range.hoy) : null;
  const dateWarning = range.tiene_fechas_futuras
    ? `Hay registros posteriores a hoy (${dayjs(range.hasta_real).format("DD/MM/YY")}). El analisis se limita hasta ${hasta.format("DD/MM/YY")}.`
    : "";
  const analysis = await loadMaterialAnalysis({
    materialId: selectedMaterialId,
    from: desde,
    to: hasta,
    horizon: forecastHorizon,
    materials: materiales,
    token,
  });

  return {
    materiales,
    presentaciones,
    fuentes,
    selectedMaterialId,
    desde,
    hasta,
    maxDate,
    dateWarning,
    ...analysis,
  };
}
