import { Alert, Box, Button, Card, CardContent, Chip, Divider, Typography } from "@mui/material";
import dayjs from "dayjs";

import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { getMapePresentation } from "./forecastMetrics.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";
import { getModelDisplayName } from "./forecastModelLabels.js";
import { getForecastTrend, getSummaryDecisionPresentation } from "./summarySemantics.js";

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

export function DecisionSummaryCard({ forecast, serie, selectedMaterial, showPrices, loading = false, error = "", onAnalyzePurchase }) {
  const selection = forecast?.seleccion_modelo || null;
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, selectedMaterial?.unidad_base || forecast?.unidad_base);
  const nextPoint = forecast?.puntos?.[0] || null;
  const trend = getForecastTrend(forecast);
  const presentationSummary = getSummaryDecisionPresentation({ forecast });
  const mape = getMapePresentation(forecast?.metricas?.mape);
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
            Estado actual de la proyección
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Una lectura compacta de la tendencia, la fecha base y el error histórico observado.
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

            {loading ? <Alert severity="info" sx={{ mt: 2 }}>Actualizando la proyección del material seleccionado.</Alert> : null}
            {!loading && error ? <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert> : null}
            {!loading && !error ? (
              <>
                <Typography mt={1.5} variant="overline" color="text.secondary">{presentationSummary.eyebrow}</Typography>
                <Typography mt={0.5} variant="h2" lineHeight={1.1}>{presentationSummary.title}</Typography>
                <Typography mt={1} color="text.secondary">{presentationSummary.description}</Typography>
                <Typography mt={1} color="text.secondary" variant="body2" fontWeight={800}>{presentationSummary.provenance}</Typography>
              </>
            ) : null}

            <Box className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MiniStat
                label="Próximo precio"
                value={nextPoint && showPrices && forecast ? formatCurrency(getDisplayPrice(nextPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                helper={nextPoint ? `${nextPoint.fecha}` : "Sin horizonte"}
              />
              <MiniStat
                label={mape.label}
                value={mape.value}
                helper={forecast?.metricas?.mape == null ? mape.explanation : "Cuanto menor, menor fue el error histórico promedio"}
              />
              <MiniStat
                label="Datos observados hasta"
                value={forecast?.ultima_fecha_observada ? dayjs(forecast.ultima_fecha_observada).format("DD/MM/YYYY") : "Sin dato"}
                helper={forecast ? `Horizonte: ${forecast.horizonte_meses} meses` : "Fecha base no disponible"}
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
              value={trend.label}
              helper={trend.deltaPct === null ? "No hay proyección" : `${formatNumber(trend.deltaPct)}% frente al último valor observado`}
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
            {onAnalyzePurchase ? (
              <Button variant="outlined" onClick={onAnalyzePurchase}>Analizar compra</Button>
            ) : null}
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
