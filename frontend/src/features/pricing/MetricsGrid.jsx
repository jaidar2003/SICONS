import { Box } from "@mui/material";
import { useState } from "react";

import { MetricCard } from "../../shared/components/MetricCard.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

export function MetricsGrid({ serie, showPrices, selectedMaterial }) {
  const [bagEquivalent, setBagEquivalent] = useState("25");

  if (!serie.length) {
    return (
      <Box className="mt-3 grid gap-3 md:grid-cols-4">
        <MetricCard label="Precio comercial" value="-" helper="Sin datos" />
        <MetricCard label="Presentacion" value="-" helper="Sin datos" />
        <MetricCard label="Ultima variacion mensual" value="-" helper="Sin datos" />
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
  const showBagEquivalents = presentation.type === "cement" && serie.some((point) => point.precio_equivalente_25kg !== null);
  const displayLastPrice = getDisplayPrice(last.precio_promedio_normalizado, selectedMaterial?.nombre, last.unidad_base);
  const selectedBagPrice = bagEquivalent === "25" ? last.precio_equivalente_25kg : last.precio_equivalente_50kg;

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
      <MetricCard label={presentation.primaryPriceLabel} value={`${formatCurrency(displayLastPrice)}`} helper={`${presentation.displayUnitLabel} · ${last.fecha}`} />
      {showBagEquivalents ? (
        <MetricCard
          label="Equivalente bolsa"
          value={formatCurrency(selectedBagPrice)}
          helper={`ARS por bolsa de ${bagEquivalent} kg`}
          control={
            <Box className="inline-flex rounded-full border border-md-primary/30 bg-white p-0.5">
              <button
                type="button"
                className={`h-5 rounded-full px-2 text-[10px] font-extrabold leading-none ${bagEquivalent === "25" ? "bg-md-primary text-white" : "text-md-primary"}`}
                onClick={() => setBagEquivalent("25")}
              >
                25
              </button>
              <button
                type="button"
                className={`h-5 rounded-full px-2 text-[10px] font-extrabold leading-none ${bagEquivalent === "50" ? "bg-md-primary text-white" : "text-md-primary"}`}
                onClick={() => setBagEquivalent("50")}
              >
                50
              </button>
            </Box>
          }
        />
      ) : null}
      {!showBagEquivalents ? <MetricCard label="Presentacion" value={presentation.fixedPresentationLabel || presentation.displayUnitLabel} helper={presentation.primaryPriceHelper} /> : null}
      {!showBagEquivalents ? (
        <MetricCard label="Ultima variacion mensual" value={lastMonthlyVariation === null ? "-" : `${formatNumber(lastMonthlyVariation)}%`} helper={last.fecha} />
      ) : null}
      {showBagEquivalents ? (
        <MetricCard
          label="Variacion mensual estimada"
          value={lastMonthlyVariation === null ? "-" : `${formatNumber(lastMonthlyVariation)}%`}
          helper={`Mes ${last.fecha}`}
        />
      ) : null}
      <MetricCard label="Variacion total" value={`${formatNumber(variation)}%`} helper={`${first.fecha} a ${last.fecha}`} />
    </Box>
  );
}
