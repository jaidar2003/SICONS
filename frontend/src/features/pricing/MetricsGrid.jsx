import { Box } from "@mui/material";

import { MetricCard } from "../../shared/components/MetricCard.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

export function MetricsGrid({ serie, showPrices, selectedMaterial }) {
  if (!serie.length) {
    return (
      <Box className="mt-3 grid gap-3 md:grid-cols-4">
        <MetricCard label="Precio comercial" value="-" helper="Sin datos" />
        <MetricCard label="Presentacion" value="-" helper="Sin datos" />
        <MetricCard label="Última variación observada" value="-" helper="Sin datos" />
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
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, last.unidad_base);
  const showBagEquivalents = presentation.type === "cement" && last.precio_equivalente_50kg !== null;
  const displayLastPrice = getDisplayPrice(last.precio_promedio_normalizado, selectedMaterial?.nombre, last.unidad_base);

  if (!showPrices) {
    return (
      <Box className="mt-3 grid gap-3 md:grid-cols-4">
        <MetricCard label="Variacion total" value={`${formatNumber(variation)}%`} helper={`${first.fecha} a ${last.fecha}`} />
        <MetricCard label="Última variación observada" value={lastMonthlyVariation === null ? "-" : `${formatNumber(lastMonthlyVariation)}%`} helper={last.fecha} />
        <MetricCard label="Promedio mensual" value={averageMonthlyVariation === null ? "-" : `${formatNumber(averageMonthlyVariation)}%`} helper="Solo cambios mensuales" />
        <MetricCard label="Meses analizados" value={String(serie.length)} helper="Serie de precios mensuales" />
      </Box>
    );
  }

  return (
    <Box className="mt-3 grid gap-3 md:grid-cols-4">
      <MetricCard label={presentation.primaryPriceLabel} value={`${formatCurrency(displayLastPrice)}`} helper={`${presentation.displayUnitLabel} · ${last.fecha}`} />
      {showBagEquivalents ? (
        <MetricCard
          label="Referencia 50 kg"
          value={formatCurrency(last.precio_equivalente_50kg)}
          helper="Equivalente historico"
        />
      ) : null}
      {!showBagEquivalents ? <MetricCard label="Presentacion" value={presentation.fixedPresentationLabel || presentation.displayUnitLabel} helper={presentation.primaryPriceHelper} /> : null}
      {!showBagEquivalents ? (
        <MetricCard label="Última variación observada" value={lastMonthlyVariation === null ? "-" : `${formatNumber(lastMonthlyVariation)}%`} helper={last.fecha} />
      ) : null}
      {showBagEquivalents ? (
        <MetricCard
          label="Variación observada"
          value={lastMonthlyVariation === null ? "-" : `${formatNumber(lastMonthlyVariation)}%`}
          helper={`Fecha ${last.fecha}`}
        />
      ) : null}
      <MetricCard label="Variacion total" value={`${formatNumber(variation)}%`} helper={`${first.fecha} a ${last.fecha}`} />
    </Box>
  );
}
