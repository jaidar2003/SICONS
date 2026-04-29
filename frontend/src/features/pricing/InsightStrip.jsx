import { Box, Typography } from "@mui/material";

import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";

export function InsightStrip({ serie, selectedMaterial, showPrices }) {
  let text = "No hay precios para el periodo seleccionado.";
  if (serie.length) {
    const first = serie[0];
    const last = serie[serie.length - 1];
    const variation = ((Number(last.precio_promedio_normalizado) - Number(first.precio_promedio_normalizado)) / Number(first.precio_promedio_normalizado)) * 100;
    text = showPrices
      ? `${selectedMaterial?.nombre || "El material"} paso de ${formatCurrency(first.precio_promedio_normalizado)} a ${formatCurrency(last.precio_promedio_normalizado)} por ${last.unidad_base}, con una variacion de ${formatNumber(variation)}% en el periodo.`
      : `${selectedMaterial?.nombre || "El material"} acumulo una variacion de ${formatNumber(variation)}% en el periodo analizado.`;
  }

  return (
    <Box className="mt-3 flex flex-col gap-2 rounded-md border border-blue-100 bg-md-container px-4 py-3 md:flex-row md:items-center">
      <Typography color="secondary" fontSize={13} fontWeight={800}>
        Lectura del periodo
      </Typography>
      <Typography color="text.secondary">{text}</Typography>
    </Box>
  );
}
