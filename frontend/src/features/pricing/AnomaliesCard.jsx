import { Alert, Box, Button, Card, CardContent, Chip, Divider, Stack, TextField, Typography } from "@mui/material";
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { Line } from "react-chartjs-2";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber, formatPercentChange, toApiDate, variationTone } from "../../shared/utils/formatters.js";
import { evaluateDetectedAnomalies } from "./pricing.api.js";
import { parseConfirmedAnomalyDates } from "./anomalyEvaluation.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export function AnomaliesCard({ serie, showPrices, selectedMaterial, token, desde, hasta, className = "" }) {
  const severityConfig = {
    leve: { label: "Leve", color: "#F59E0B", bg: "#FFF7ED" },
    media: { label: "Media", color: "#F97316", bg: "#FFF7ED" },
    alta: { label: "Alta", color: "#DC2626", bg: "#FEF2F2" },
  };
  const [confirmedDatesInput, setConfirmedDatesInput] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const [evaluationError, setEvaluationError] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const anomalies = serie.filter((point) => point.es_anomalia);
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, serie[0]?.unidad_base);
  const labels = serie.map((point) => point.fecha.slice(0, 7));
  const firstDate = serie[0]?.fecha || "";
  const lastDate = serie[serie.length - 1]?.fecha || "";
  const mainSeries = showPrices
    ? serie.map((point) => getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))
    : serie.map((point) => Number(point.variacion_porcentual_anterior || 0));
  const anomalySeries = serie.map((point, index) => (point.es_anomalia ? mainSeries[index] : null));
  const chartLabel = showPrices ? presentation.primaryPriceLabel : "Variacion mensual %";
  const evaluationSummary = useMemo(() => {
    if (!evaluation) return null;
    return [
      {
        label: "Precisión",
        value: formatRatio(evaluation.precision),
        helper: "Coincidencias sobre lo detectado",
      },
      {
        label: "Recall",
        value: formatRatio(evaluation.recall),
        helper: "Coincidencias sobre lo confirmado",
      },
      {
        label: "F1",
        value: formatRatio(evaluation.f1),
        helper: "Balance entre precisión y recall",
      },
      {
        label: "Exactitud",
        value: formatRatio(evaluation.exactitud),
        helper: "Aciertos sobre el total evaluado",
      },
    ];
  }, [evaluation]);

  useEffect(() => {
    setConfirmedDatesInput("");
    setEvaluation(null);
    setEvaluationError("");
    setEvaluating(false);
  }, [selectedMaterial?.id, firstDate, lastDate]);

  async function handleEvaluate() {
    setEvaluationError("");
    setEvaluation(null);

    if (!selectedMaterial?.id) {
      setEvaluationError("Seleccioná un material.");
      return;
    }

    if (!token) {
      setEvaluationError("Iniciá sesión para evaluar anomalías.");
      return;
    }

    const parsed = parseConfirmedAnomalyDates(confirmedDatesInput);
    if (parsed.invalidValues.length) {
      setEvaluationError(`Hay fechas inválidas: ${parsed.invalidValues.join(", ")}`);
      return;
    }

    if (!parsed.dates.length) {
      setEvaluationError("Pegá al menos una fecha confirmada, una por línea.");
      return;
    }

    setEvaluating(true);
    try {
      const result = await evaluateDetectedAnomalies({
        materialId: selectedMaterial.id,
        fechasConfirmadas: parsed.dates,
        desde: desde ? toApiDate(dayjs(desde)) : undefined,
        hasta: hasta ? toApiDate(dayjs(hasta)) : undefined,
        token,
      });
      setEvaluation(result);
    } catch (error) {
      setEvaluationError(error.message);
    } finally {
      setEvaluating(false);
    }
  }

  const chartData = {
    labels,
    datasets: [
      {
        label: chartLabel,
        data: mainSeries,
        borderColor: "#002395",
        backgroundColor: "rgba(0, 35, 149, 0.10)",
        fill: true,
        borderWidth: 2.5,
        tension: 0.25,
        pointRadius: 2,
        pointHoverRadius: 5,
        pointBackgroundColor: "#FEFBFF",
        pointBorderColor: "#002395",
        pointBorderWidth: 1.5,
      },
      {
        label: "Anomalia Random Forest",
        data: anomalySeries,
        borderColor: "rgba(237, 41, 57, 0)",
        backgroundColor: "#ED2939",
        pointRadius: 7,
        pointHoverRadius: 9,
        pointBackgroundColor: "#ED2939",
        pointBorderColor: "#ffffff",
        pointBorderWidth: 2.5,
        showLine: false,
      },
    ],
  };
  const chartOptions = {
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom" },
      tooltip: {
        callbacks: {
          label(context) {
            const point = serie[context.dataIndex];
            if (context.datasetIndex === 1 && point?.es_anomalia) {
              return [
                "Anomalia detectada por Random Forest",
                point.motivo_anomalia || "Mes atipico frente al patron esperado.",
              ];
            }
            if (showPrices) {
              return [
                `${chartLabel}: ${formatCurrency(context.parsed.y)}`,
                `Variacion mensual: ${point?.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point?.variacion_porcentual_anterior)}%`}`,
              ];
            }
            return `Variacion mensual: ${formatNumber(context.parsed.y)}%`;
          },
        },
      },
    },
    scales: {
      x: { grid: { display: false } },
      y: {
        title: {
          display: true,
          text: showPrices ? presentation.chartAxisLabel : "Variacion mensual %",
        },
        ticks: {
          callback: (value) =>
            showPrices
              ? Number(value).toLocaleString("es-AR", { maximumFractionDigits: 0 })
              : `${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 1 })}%`,
        },
      },
    },
  };

  return (
    <Card className={`h-full ${className}`}>
      <CardContent>
        <SectionHeader title="Variaciones bruscas" description="Meses detectados como atípicos por el modelo Random Forest." />
        <Box className="chart-shell anomaly-chart-shell mb-5 h-[340px]">
          <Line data={chartData} options={chartOptions} redraw />
        </Box>
        {!anomalies.length ? (
          <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
            No se detectaron variaciones mensuales bruscas en el periodo seleccionado.
          </Box>
        ) : (
          <Box className="grid gap-3 xl:grid-cols-2">
            {anomalies.map((point) => {
              const parsedMotivo = parseAnomalyMotivo(point.motivo_anomalia);
              return (
                <Box
                  key={point.fecha}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
                  sx={{
                    borderLeftWidth: 6,
                    borderLeftStyle: "solid",
                    borderLeftColor: severityColor(point.severidad_anomalia, severityConfig),
                  }}
                >
                  <Box className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                    <Box className="flex flex-wrap items-start justify-between gap-2">
                      <Box>
                        <Typography variant="overline" color="text.secondary">
                          Mes detectado
                        </Typography>
                        <Typography variant="h4" lineHeight={1.1}>
                          {point.fecha.slice(0, 7)}
                        </Typography>
                      </Box>
                      {point.severidad_anomalia ? (
                        <Chip
                          label={`Severidad ${severityConfig[point.severidad_anomalia]?.label || point.severidad_anomalia}`}
                          size="small"
                          sx={{
                            fontWeight: 800,
                            backgroundColor: severityConfig[point.severidad_anomalia]?.bg || "#F8FAFC",
                            color: severityConfig[point.severidad_anomalia]?.color || "#0F172A",
                            borderColor: severityConfig[point.severidad_anomalia]?.color || "#CBD5E1",
                          }}
                          variant="outlined"
                        />
                      ) : null}
                    </Box>
                    <Box className="mt-2 flex flex-wrap gap-1.5">
                      <Chip
                        label={formatPercentChange(point.variacion_porcentual_anterior)}
                        size="small"
                        sx={{
                          color: variationTone(point.variacion_porcentual_anterior),
                          fontWeight: 800,
                          backgroundColor: "#FFFFFF",
                        }}
                      />
                    <Chip
                      label={point.cantidad_registros === 1 ? "1 precio relevado" : `${point.cantidad_registros} precios relevados`}
                      size="small"
                      variant="outlined"
                      sx={{ fontWeight: 800 }}
                    />
                    {point.score_anomalia !== null && point.score_anomalia !== undefined ? (
                      <Chip
                        label={`Score ${point.score_anomalia}/4`}
                        size="small"
                        variant="outlined"
                        sx={{ fontWeight: 800 }}
                      />
                    ) : null}
                    {point.confianza_anomalia !== null && point.confianza_anomalia !== undefined ? (
                      <Chip
                        label={`Confianza ${formatPercent(point.confianza_anomalia)}`}
                        size="small"
                        sx={{
                          fontWeight: 800,
                          backgroundColor: "#EFF6FF",
                          color: "#1D4ED8",
                        }}
                      />
                    ) : null}
                    {showPrices ? (
                      <Chip
                        label={formatCurrency(getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))}
                        size="small"
                        variant="outlined"
                          sx={{ fontWeight: 800 }}
                        />
                      ) : null}
                    </Box>
                  </Box>

                  <Box className="px-4 py-3">
                    <Typography color="text.secondary" fontSize={12}>
                      {point.fuentes?.length ? point.fuentes.join(" / ") : "Sin fuente visible"}
                      {showPrices ? ` · ${presentation.displayUnitLabel}` : ""}
                    </Typography>

                    <Box className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <Typography color="text.secondary" variant="caption" fontWeight={900} letterSpacing={0}>
                        Explicación del modelo
                      </Typography>
                      <Typography mt={0.5} variant="body2" color="text.primary">
                        {parsedMotivo.summary}
                      </Typography>
                    </Box>

                    {parsedMotivo.signals.length ? (
                      <Box className="mt-2 flex flex-wrap gap-1.5">
                        {parsedMotivo.signals.map((signal) => (
                          <Chip
                            key={signal}
                            label={signal}
                            size="small"
                            variant="outlined"
                            sx={{
                              fontSize: 12,
                              height: 26,
                              backgroundColor: "#FFFFFF",
                              borderColor: "#CBD5E1",
                              color: "#334155",
                            }}
                          />
                        ))}
                      </Box>
                    ) : null}
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}

        <Divider className="!my-5" />

        <Stack spacing={2.5}>
          <Box>
            <Typography variant="h4">Validación de anomalías</Typography>
            <Typography color="text.secondary" variant="body2" mt={0.5}>
              Pegá una fecha por línea, o separalas con comas. La evaluación usa el rango visible {firstDate && lastDate ? `${firstDate.slice(0, 7)} a ${lastDate.slice(0, 7)}` : "del historial actual"}.
            </Typography>
          </Box>

          <TextField
            value={confirmedDatesInput}
            onChange={(event) => setConfirmedDatesInput(event.target.value)}
            label="Fechas confirmadas"
            placeholder="2026-02-01\n2026-05-01"
            helperText="Usá fechas ISO de meses confirmados. También podés pegar meses como YYYY-MM."
            multiline
            minRows={4}
            fullWidth
          />

          <Box className="flex flex-wrap gap-2">
            <Button variant="contained" onClick={handleEvaluate} disabled={evaluating || !selectedMaterial?.id}>
              {evaluating ? "Evaluando..." : "Evaluar contra confirmadas"}
            </Button>
            <Button
              variant="outlined"
              onClick={() => {
                setConfirmedDatesInput("");
                setEvaluation(null);
                setEvaluationError("");
              }}
              disabled={!confirmedDatesInput && !evaluation && !evaluationError}
            >
              Limpiar
            </Button>
          </Box>

          {evaluationError ? <Alert severity="error">{evaluationError}</Alert> : null}

          {evaluating ? (
            <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
              Calculando precision, recall, F1 y exactitud...
            </Box>
          ) : null}

          {evaluation ? (
            <Box className="rounded-md border border-slate-200 bg-white p-4">
              <Box className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {evaluationSummary.map((item) => (
                  <MetricTile key={item.label} label={item.label} value={item.value} helper={item.helper} />
                ))}
              </Box>

              <Box className="mt-4 grid gap-3 sm:grid-cols-3">
                <MetricTile label="Confirmadas" value={String(evaluation.total_confirmadas)} helper="Fechas ingresadas" />
                <MetricTile label="Detectadas" value={String(evaluation.total_detectadas)} helper="Marcas del modelo" />
                <MetricTile label="Coincidencias" value={String(evaluation.verdaderos_positivos)} helper="Aciertos sobre la validación" />
              </Box>

              <Box className="mt-3 grid gap-3 sm:grid-cols-2">
                <MetricTile label="Falsos positivos" value={String(evaluation.falsos_positivos)} helper="Marcados por el modelo pero no confirmados" />
                <MetricTile label="Falsos negativos" value={String(evaluation.falsos_negativos)} helper="Confirmados pero no detectados" />
              </Box>

              <Box className="mt-4 grid gap-3 lg:grid-cols-2">
                <DetailList title="Coincidencias" values={evaluation.coincidencias} emptyText="No hubo coincidencias." />
                <DetailList title="Fechas detectadas" values={evaluation.fechas_detectadas} emptyText="El modelo no marcó anomalías en el rango." />
              </Box>

              <DetailList className="mt-3" title="Fechas confirmadas" values={evaluation.fechas_confirmadas} emptyText="No se cargaron fechas confirmadas." />
            </Box>
          ) : (
            <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
              Cargá fechas confirmadas para medir qué tan preciso está el detector frente a anomalías reales.
            </Box>
          )}

          <Box className="rounded-xl border border-slate-200 bg-white p-4">
            <Box className="flex items-start justify-between gap-3">
              <Box>
                <Typography variant="h4">Glosario</Typography>
                <Typography color="text.secondary" variant="body2" mt={0.5}>
                  Qué significa cada señal y de dónde sale.
                </Typography>
              </Box>
              <Chip label="Auditable" size="small" variant="outlined" sx={{ fontWeight: 800 }} />
            </Box>

            <Box className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <GlossaryItem
                term="Residuo"
                definition="Distancia porcentual entre el precio observado y el precio esperado por el Random Forest."
              />
              <GlossaryItem
                term="Desvío de tendencia"
                definition="Diferencia porcentual contra una tendencia local de corto plazo, calculada con los últimos meses."
              />
              <GlossaryItem
                term="Gap estacional"
                definition="Diferencia frente al mismo mes de años anteriores, si existe un antecedente comparable."
              />
              <GlossaryItem
                term="Score"
                definition="Cantidad de señales activadas sobre 4: residuo, variación mensual, estacionalidad y tendencia."
              />
              <GlossaryItem
                term="Confianza"
                definition="Porcentaje heurístico derivado del score y de la fuerza del residuo. Sirve para priorizar revisión."
              />
              <GlossaryItem
                term="Severidad"
                definition="Etiqueta cualitativa que resume qué tan fuerte fue la desviación detectada."
              />
              <GlossaryItem
                term="Precisión"
                definition="Métrica global de evaluación contra anomalías confirmadas. No se asigna por punto individual."
              />
              <GlossaryItem
                term="Recall"
                definition="Proporción de anomalías confirmadas que el detector logró encontrar."
              />
              <GlossaryItem
                term="F1"
                definition="Balance entre precisión y recall. Útil cuando querés medir detección y falsos positivos al mismo tiempo."
              />
            </Box>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

function MetricTile({ label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} variant="h3" lineHeight={1.1}>
        {value}
      </Typography>
      <Typography color="text.secondary" variant="body2" mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}

function DetailList({ title, values, emptyText, className = "" }) {
  return (
    <Box className={`rounded-xl border border-slate-200 bg-slate-50 p-3 ${className}`}>
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {title}
      </Typography>
      {values?.length ? (
        <Box className="mt-2 flex flex-wrap gap-1.5">
          {values.map((value) => (
            <Chip key={String(value)} label={String(value)} size="small" />
          ))}
        </Box>
      ) : (
        <Typography color="text.secondary" variant="body2" mt={0.75}>
          {emptyText}
        </Typography>
      )}
    </Box>
  );
}

function GlossaryItem({ term, definition }) {
  return (
    <Box className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <Typography variant="body2" fontWeight={900} color="text.primary">
        {term}
      </Typography>
      <Typography variant="body2" color="text.secondary" mt={0.5}>
        {definition}
      </Typography>
    </Box>
  );
}

function formatRatio(value) {
  if (value === null || value === undefined) return "Sin dato";
  return `${formatNumber(Number(value) * 100)}%`;
}

function formatPercent(value) {
  if (value === null || value === undefined) return "Sin dato";
  return `${formatNumber(Number(value))}%`;
}

function parseAnomalyMotivo(value) {
  const raw = String(value || "").trim();
  if (!raw) {
    return {
      summary: "Mes atípico frente al patrón esperado.",
      signals: [],
    };
  }

  const parts = raw.split(": ");
  const summary = parts.length > 1 ? parts.slice(1).join(": ") : raw;
  const signals = summary
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => !item.toLowerCase().startsWith("precio esperado"));

  return {
    summary: parts[0] && parts.length > 1 ? `${parts[0]}: ${signals.length ? signals[0] : summary.split(";")[0].trim()}` : summary,
    signals,
  };
}

function severityColor(severity, severityConfig) {
  return severityConfig[severity]?.color || "#CBD5E1";
}
