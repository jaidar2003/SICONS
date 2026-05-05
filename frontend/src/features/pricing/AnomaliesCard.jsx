import { Box, Card, CardContent, Chip, Typography } from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatPercentChange, variationTone } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

export function AnomaliesCard({ serie, showPrices, selectedMaterial }) {
  const anomalies = serie.filter((point) => point.es_anomalia);
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, serie[0]?.unidad_base);

  return (
    <Card>
      <CardContent>
        <SectionHeader title="Variaciones bruscas" description="Meses donde el cambio supera el umbral definido." />
        {!anomalies.length ? (
          <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
            No se detectaron variaciones mensuales bruscas en el periodo seleccionado.
          </Box>
        ) : (
          <Box className="grid gap-2 sm:grid-cols-2">
            {anomalies.map((point) => (
              <Box key={point.fecha} className="rounded-md border border-slate-200 bg-white px-3 py-2">
                <Typography fontWeight={800}>{point.fecha.slice(0, 7)}</Typography>
                <Chip label={formatPercentChange(point.variacion_porcentual_anterior)} size="small" sx={{ color: variationTone(point.variacion_porcentual_anterior), fontWeight: 800 }} />
                {showPrices ? (
                  <Typography color="text.secondary" fontSize={12} mt={0.75}>
                    {formatCurrency(getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))} · {presentation.displayUnitLabel}
                  </Typography>
                ) : (
                  <Typography color="text.secondary" fontSize={12} mt={0.75}>
                    {point.cantidad_registros} {point.cantidad_registros === 1 ? "precio relevado" : "precios relevados"}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
