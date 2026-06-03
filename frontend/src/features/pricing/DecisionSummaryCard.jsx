import { Box, Card, CardContent, Chip, Divider, Typography } from "@mui/material";

import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";
import { getModelDisplayName } from "./forecastModelLabels.js";

function confidenceColor(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "alta") return "success";
  if (normalized === "media") return "warning";
  if (normalized === "baja") return "error";
  return "default";
}

function anomalySeverityLabel(points) {
  const anomalies = points.filter((point) => point.es_anomalia);
  if (!anomalies.length) return "Serie sin anomalías";

  const severities = anomalies.reduce(
    (acc, point) => {
      const severity = String(point.severidad_anomalia || "").toLowerCase();
      if (severity === "alta") acc.alta += 1;
      else if (severity === "media") acc.media += 1;
      else if (severity === "leve") acc.leve += 1;
      return acc;
    },
    { leve: 0, media: 0, alta: 0 }
  );

  if (severities.alta > 0) return `Serie con ${severities.alta} anomalía${severities.alta === 1 ? "" : "s"} alta${severities.alta === 1 ? "" : "s"}`;
  if (severities.media > 0) return `Serie con ${severities.media} anomalía${severities.media === 1 ? "" : "s"} media${severities.media === 1 ? "" : "s"}`;
  return `Serie con ${severities.leve} anomalía${severities.leve === 1 ? "" : "s"} leve${severities.leve === 1 ? "" : "s"}`;
}

export function DecisionSummaryCard({ forecast, serie, selectedMaterial, showPrices }) {
  const selection = forecast?.seleccion_modelo || null;
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, selectedMaterial?.unidad_base || forecast?.unidad_base);
  const nextPoint = forecast?.puntos?.[0] || null;
  const lastObservedValue = Number(forecast?.ultimo_precio_observado || 0);
  const nextForecastValue = Number(nextPoint?.precio_proyectado || 0);
  const deltaPct =
    forecast && nextPoint && lastObservedValue > 0
      ? ((nextForecastValue - lastObservedValue) / lastObservedValue) * 100
      : null;
  const decisionText =
    deltaPct === null
      ? "Sin forecast disponible"
      : deltaPct > 0
        ? "Anticipar compra"
        : deltaPct < 0
          ? "Esperar si no es urgente"
          : "Revisar urgencia";
  const anomaliesLabel = anomalySeverityLabel(serie || []);
  const anomalyCount = (serie || []).filter((point) => point.es_anomalia).length;

  return (
    <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
      <CardContent className="p-0">
        <Box className="border-b border-slate-200 bg-slate-50 px-4 py-3">
          <Typography variant="overline" color="text.secondary">
            Sintesis operativa
          </Typography>
          <Typography mt={0.5} variant="h3">
            Estado actual de la decision
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Una lectura compacta del forecast, la calidad de la serie y la accion sugerida.
          </Typography>
        </Box>

        <Box className="grid gap-0 md:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)]">
          <Box className="p-4 md:p-5">
            <Box className="flex flex-wrap gap-2">
              <Chip label={selectedMaterial?.nombre || "Sin material"} sx={{ fontWeight: 800 }} />
              <Chip label={selection ? getModelDisplayName(selection.modelo_resuelto) : "Sin modelo"} variant="outlined" sx={{ fontWeight: 800 }} />
              <Chip
                label={selection?.confiabilidad || "sin dato"}
                color={confidenceColor(selection?.confiabilidad)}
                variant="outlined"
                sx={{ fontWeight: 800, textTransform: "uppercase" }}
              />
            </Box>

            <Typography mt={1.5} variant="h2" lineHeight={1.1}>
              {decisionText}
            </Typography>
            <Typography mt={1} color="text.secondary">
              {forecast
                ? `El sistema resume la proyeccion de ${selectedMaterial?.nombre || "el material"} con datos propios y reglas auditables.`
                : "Todavia no hay una proyeccion disponible para sintetizar."}
            </Typography>

            <Box className="mt-4 grid gap-3 sm:grid-cols-3">
              <MiniStat
                label="Próximo precio"
                value={nextPoint && showPrices && forecast ? formatCurrency(getDisplayPrice(nextPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                helper={nextPoint ? `${nextPoint.fecha}` : "Sin horizonte"}
              />
              <MiniStat
                label="MAPE"
                value={forecast?.metricas?.mape !== null && forecast?.metricas?.mape !== undefined ? `${formatNumber(forecast.metricas.mape)}%` : "Sin dato"}
                helper={forecast?.metricas?.folds ? `${forecast.metricas.folds} folds` : "Backtesting temporal"}
              />
              <MiniStat
                label="Anomalías"
                value={String(anomalyCount)}
                helper={anomaliesLabel}
              />
            </Box>
          </Box>

          <Box className="grid gap-3 border-t border-slate-200 bg-white p-4 md:border-l md:border-t-0">
            <MiniStat
              label="Tendencia"
              value={
                deltaPct === null ? "Sin forecast" : deltaPct > 0 ? "Alcista" : deltaPct < 0 ? "Bajista" : "Estable"
              }
              helper={deltaPct === null ? "No hay proyección" : `${formatNumber(deltaPct)}% frente al último valor observado`}
            />
            <Divider />
            <MiniStat
              label="Lectura del modelo"
              value={selection?.no_calibrado ? "No calibrado" : "Calibrado"}
              helper={selection?.justificacion || "Sin detalle técnico"}
            />
            {selection?.advertencia ? (
              <>
                <Divider />
                <Typography color="text.secondary" variant="body2" fontWeight={800}>
                  Advertencia
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  {selection.advertencia}
                </Typography>
              </>
            ) : null}
            <Divider />
            <Typography color="text.secondary" variant="body2" fontWeight={800}>
              Presentación
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {presentation.summaryUnitText}
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} variant="h3" lineHeight={1.15}>
        {value}
      </Typography>
      <Typography color="text.secondary" variant="body2" mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
