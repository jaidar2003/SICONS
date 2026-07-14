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

export async function loadForecastExtras({ materialId, horizon, token }) {
  if (!materialId) {
    return {
      forecast: null,
      commercialPrice: null,
    };
  }

  const [forecast, commercialPrice] = await Promise.all([
    fetchForecast({ materialId, horizonteMeses: horizon, token }).catch(() => null),
    fetchCommercialPrice({ materialId, horizonteMeses: horizon, token }).catch(() => null),
  ]);

  return { forecast, commercialPrice };
}

export async function loadComparisonRows({ materials, from, to, token }) {
  if (!materials?.length) return [];

  const desde = toApiDate(from);
  const hasta = toApiDate(to);
  const comparisonResults = await Promise.all(
    materials.map(async (material) => ({
      material,
      serie: await fetchSerie({ materialId: material.id, desde, hasta, token }),
    }))
  );

  return buildComparisonRows(comparisonResults);
}

export async function loadMaterialAnalysis({
  materialId,
  from,
  to,
  horizon,
  token,
  includeForecast = true,
  includeCommercial = true,
}) {
  if (!materialId) {
    return {
      serie: [],
      forecast: null,
      commercialPrice: null,
    };
  }

  const desde = toApiDate(from);
  const hasta = toApiDate(to);
  const [serie, forecast, commercialPrice] = await Promise.all([
    fetchSerie({ materialId, desde, hasta, token }),
    includeForecast ? fetchForecast({ materialId, horizonteMeses: horizon, token }).catch(() => null) : Promise.resolve(null),
    includeCommercial ? fetchCommercialPrice({ materialId, horizonteMeses: horizon, token }).catch(() => null) : Promise.resolve(null),
  ]);

  return {
    serie,
    forecast,
    commercialPrice,
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
  const desde = rangeDesde ?? clientDefaultStart;
  const hasta = dayjs(range.hasta || range.hoy);
  const maxDate = range.hoy ? dayjs(range.hoy) : null;
  const dateWarning = "";
  const analysis = await loadMaterialAnalysis({
    materialId: selectedMaterialId,
    from: desde,
    to: hasta,
    horizon: forecastHorizon,
    materials: materiales,
    token,
    includeForecast: false,
    includeCommercial: false,
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
    comparisonRows: [],
    forecast: null,
    commercialPrice: null,
    ...analysis,
  };
}
