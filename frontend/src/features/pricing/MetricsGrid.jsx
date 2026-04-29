import { Box } from "@mui/material";

import { MetricCard } from "../../shared/components/MetricCard.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";

export function MetricsGrid({ serie, showPrices }) {
  if (!serie.length) {
    return (
      <Box className="mt-3 grid gap-3 md:grid-cols-4">
        <MetricCard label="Ultimo precio normalizado" value="-" helper="Sin datos" />
        <MetricCard label="Equivalente 25 kg" value="-" helper="ARS por bolsa" />
        <MetricCard label="Equivalente 50 kg" value="-" helper="ARS por bolsa" />
        <MetricCard label="Variacion total" value="-" helper="-" />
      </Box>
    );
  }

  const first = serie[0];
  const last = serie[serie.length - 1];
  const variation = ((Number(last.precio_promedio_normalizado) - Number(first.precio_promedio_normalizado)) / Number(first.precio_promedio_normalizado)) * 100;
  const lastMonthlyVariation = last.variacion_porcentual_anterior === null ? null : Number(last.variacion_porcentual_anterior);
  const monthlyVariations = serie
    .map((point) => (point.variacion_porcentual_anterior === null ? null : Number(point.variacion_porcentual_anterior)))
    .filter((value) => value !== null);
  const averageMonthlyVariation = monthlyVariations.length
    ? monthlyVariations.reduce((total, value) => total + value, 0) / monthlyVariations.length
    : null;

  if (!showPrices) {
    return (
      <Box className="mt-3 grid gap-3 md:grid-cols-4">
        <MetricCard label="Variacion total" value={`${formatNumber(variation)}%`} helper={`${first.fecha} a ${last.fecha}`} />
        <MetricCard label="Ultima variacion mensual" value={lastMonthlyVariation === null ? "-" : `${formatNumber(lastMonthlyVariation)}%`} helper={last.fecha} />
        <MetricCard label="Promedio variacion mensual" value={averageMonthlyVariation === null ? "-" : `${formatNumber(averageMonthlyVariation)}%`} helper="Solo cambios observados" />
        <MetricCard label="Meses analizados" value={String(serie.length)} helper="Serie mensual" />
      </Box>
    );
  }

  return (
    <Box className="mt-3 grid gap-3 md:grid-cols-4">
      <MetricCard label="Ultimo precio normalizado" value={`${formatCurrency(last.precio_promedio_normalizado)} / ${last.unidad_base}`} helper={last.fecha} />
      <MetricCard label="Equivalente 25 kg" value={formatCurrency(last.precio_equivalente_25kg)} helper="ARS por bolsa" />
      <MetricCard label="Equivalente 50 kg" value={formatCurrency(last.precio_equivalente_50kg)} helper="ARS por bolsa" />
      <MetricCard label="Variacion total" value={`${formatNumber(variation)}%`} helper={`${first.fecha} a ${last.fecha}`} />
    </Box>
  );
}
