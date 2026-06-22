import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip } from "chart.js";
import dayjs from "dayjs";
import { useEffect, useMemo, useRef, useState } from "react";
import { Bar, getElementAtEvent } from "react-chartjs-2";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber, formatPercentChange, toApiDate, variationTone } from "../../shared/utils/formatters.js";
import { evaluateDetectedAnomalies, fetchSerie } from "./pricing.api.js";
import { parseConfirmedAnomalyDates } from "./anomalyEvaluation.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

ChartJS.register(LinearScale, CategoryScale, BarElement, Tooltip);

const GLOSSARY_ITEMS = [
  ["Residuo", "Distancia porcentual entre el precio observado y el precio esperado por el Random Forest."],
  ["Desvío de tendencia", "Diferencia porcentual contra una tendencia local de corto plazo, calculada con los últimos meses."],
  ["Gap estacional", "Diferencia frente al mismo mes de años anteriores, si existe un antecedente comparable."],
  ["Score", "Cantidad de señales activadas sobre 4: residuo, variación entre observaciones, estacionalidad y tendencia."],
  ["Confianza", "Porcentaje heurístico derivado del score y de la fuerza del residuo. Sirve para priorizar revisión."],
  ["Severidad", "Etiqueta cualitativa que resume qué tan fuerte fue la desviación detectada."],
  ["Rango normal", "Banda esperada alrededor del precio estimado por Random Forest, calculada con el límite dinámico de residuo."],
  ["Tipo", "Clasificación operativa: salto puntual, desvío de tendencia, desvío estacional, cambio sostenido o residuo extremo."],
  ["Baseline", "Regla simple de comparación que marca observaciones con una variación mayor al umbral fijo."],
  ["Precisión", "Proporción de alertas del modelo que coinciden con anomalías confirmadas."],
  ["Recall", "Proporción de anomalías confirmadas que el detector logró encontrar."],
  ["F1", "Balance entre precisión y recall; resume detección y falsos positivos en una sola métrica."],
];

function buildMonthlyAnomalySeries(points, values) {
  const buckets = new Map();
  points.forEach((point, index) => {
    const monthKey = dayjs(point.fecha).format("YYYY-MM");
    const bucket = buckets.get(monthKey) || {
      monthKey,
      label: dayjs(point.fecha).format("MMM YYYY"),
      values: [],
      dates: [],
      severities: [],
      rawPoints: [],
    };
    bucket.values.push(Number(values[index] ?? 0));
    bucket.dates.push(point.fecha);
    bucket.severities.push(point.severidad_anomalia);
    bucket.rawPoints.push(point);
    buckets.set(monthKey, bucket);
  });

  return [...buckets.values()]
    .sort((a, b) => a.monthKey.localeCompare(b.monthKey))
    .map((bucket) => {
      const severityRank = { alta: 3, media: 2, leve: 1 };
      const dominantSeverity = bucket.severities.reduce((current, severity) => {
        return (severityRank[severity] || 0) > (severityRank[current] || 0) ? severity : current;
      }, bucket.severities[0] || "media");
      const sum = bucket.values.reduce((acc, value) => acc + value, 0);
      const average = bucket.values.length ? sum / bucket.values.length : 0;
      const max = bucket.values.length ? Math.max(...bucket.values) : 0;
      const min = bucket.values.length ? Math.min(...bucket.values) : 0;
      return {
        x: bucket.label,
        y: average,
        monthKey: bucket.monthKey,
        count: bucket.values.length,
        dates: bucket.dates,
        severities: bucket.severities,
        dominantSeverity,
        average,
        max,
        min,
        points: bucket.rawPoints,
      };
    });
}

export function AnomaliesCard({ serie, showPrices, selectedMaterial, token, desde, hasta, className = "" }) {
  const severityConfig = {
    leve: { label: "Leve", color: "#F59E0B", bg: "#FFF7ED" },
    media: { label: "Media", color: "#F97316", bg: "#FFF7ED" },
    alta: { label: "Alta", color: "#DC2626", bg: "#FEF2F2" },
  };
  const severityFilters = [
    { value: "todas", label: "Todas" },
    { value: "alta", label: "Alta" },
    { value: "media", label: "Media" },
    { value: "leve", label: "Leve" },
  ];
  const [confirmedDatesInput, setConfirmedDatesInput] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const [evaluationError, setEvaluationError] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [anomalySerie, setAnomalySerie] = useState(null);
  const [seriesLoading, setSeriesLoading] = useState(false);
  const [seriesError, setSeriesError] = useState("");
  const [severityFilter, setSeverityFilter] = useState("todas");
  const [selectedMonthKey, setSelectedMonthKey] = useState(null);
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const chartRef = useRef(null);
  const anomalies = useMemo(() => (anomalySerie ?? []).filter((point) => point.es_anomalia), [anomalySerie]);
  const visibleAnomalies = useMemo(
    () => (severityFilter === "todas" ? anomalies : anomalies.filter((point) => point.severidad_anomalia === severityFilter)),
    [anomalies, severityFilter]
  );
  const chartSerie = visibleAnomalies;
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, chartSerie[0]?.unidad_base || serie[0]?.unidad_base);
  const firstDate = chartSerie[0]?.fecha || "";
  const lastDate = chartSerie[chartSerie.length - 1]?.fecha || "";
  const mainSeries = showPrices
    ? chartSerie.map((point) => getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))
    : chartSerie.map((point) => Number(point.variacion_porcentual_anterior || 0));
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

  const chartPoints = useMemo(() => buildMonthlyAnomalySeries(chartSerie, mainSeries), [chartSerie, mainSeries]);
  const selectedMonthData = useMemo(
    () => chartPoints.find((point) => point.monthKey === selectedMonthKey) || chartPoints[0] || null,
    [chartPoints, selectedMonthKey]
  );
  const selectedMonthAnomalies = useMemo(() => {
    if (!selectedMonthData) return [];
    return chartSerie.filter((point) => dayjs(point.fecha).format("YYYY-MM") === selectedMonthData.monthKey);
  }, [chartSerie, selectedMonthData]);
  const anomalyInterval = useMemo(() => {
    if (!chartPoints.length) return null;
    const first = dayjs(`${chartPoints[0].monthKey}-01`);
    const last = dayjs(`${chartPoints[chartPoints.length - 1].monthKey}-01`);
    if (!first.isValid() || !last.isValid()) return null;
    return {
      firstLabel: first.format("MMM YYYY"),
      lastLabel: last.format("MMM YYYY"),
      firstKey: chartPoints[0].monthKey,
      lastKey: chartPoints[chartPoints.length - 1].monthKey,
    };
  }, [chartPoints]);

  const chartColors = useMemo(
    () =>
      chartPoints.map((point) => {
        const config = severityConfig[point.dominantSeverity] || severityConfig.media;
        return config.color;
      }),
    [chartPoints]
  );
  const chartBackgroundColors = useMemo(
    () =>
      chartPoints.map((point) => {
        const config = severityConfig[point.dominantSeverity] || severityConfig.media;
        return !selectedMonthKey || selectedMonthKey === point.monthKey ? config.color : `${config.color}55`;
      }),
    [chartPoints, selectedMonthKey]
  );
  const baselineSummary = useMemo(() => {
    if (!evaluation) return null;
    return [
      {
        label: "Precisión",
        value: formatRatio(evaluation.baseline_precision),
        helper: `Regla fija > ${formatPercent(evaluation.baseline_umbral_pct)}`,
      },
      {
        label: "Recall",
        value: formatRatio(evaluation.baseline_recall),
        helper: "Confirmadas encontradas",
      },
      {
        label: "F1",
        value: formatRatio(evaluation.baseline_f1),
        helper: "Balance baseline",
      },
      {
        label: "Detectadas",
        value: String(evaluation.baseline_total_detectadas),
        helper: "Marcas por umbral fijo",
      },
    ];
  }, [evaluation]);

  useEffect(() => {
    setConfirmedDatesInput("");
    setEvaluation(null);
    setEvaluationError("");
    setEvaluating(false);
    setSeverityFilter("todas");
    setSelectedMonthKey(null);
  }, [selectedMaterial?.id, firstDate, lastDate]);

  useEffect(() => {
    if (!chartPoints.length) {
      setSelectedMonthKey(null);
      return;
    }
    setSelectedMonthKey((current) => (current && chartPoints.some((point) => point.monthKey === current) ? current : chartPoints[0].monthKey));
  }, [chartPoints]);

  useEffect(() => {
    let active = true;
    async function loadAnomalySerie() {
      if (!selectedMaterial?.id || !token) {
        setAnomalySerie([]);
        setSeriesError("");
        setSeriesLoading(false);
        return;
      }

      setSeriesLoading(true);
      setSeriesError("");
      try {
        const result = await fetchSerie({
          materialId: selectedMaterial.id,
          desde: desde ? toApiDate(dayjs(desde)) : undefined,
          hasta: hasta ? toApiDate(dayjs(hasta)) : undefined,
          token,
          agrupacion: "observaciones",
        });
        if (!active) return;
        setAnomalySerie(result || []);
      } catch (error) {
        if (!active) return;
        setSeriesError(error.message);
        setAnomalySerie([]);
      } finally {
        if (active) setSeriesLoading(false);
      }
    }

    loadAnomalySerie();
    return () => {
      active = false;
    };
  }, [selectedMaterial?.id, desde, hasta, token]);

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
    labels: chartPoints.map((point) => point.x),
    datasets: [
      {
        label: showPrices ? "Precio anómalo mensual promedio" : "Variación anómala mensual promedio %",
        data: chartPoints.map((point) => point.y),
        borderColor: chartColors,
        backgroundColor: chartBackgroundColors,
        borderWidth: 0,
        borderRadius: 8,
        barThickness: 28,
        maxBarThickness: 34,
      },
    ],
  };
  const chartOptions = {
    maintainAspectRatio: false,
    interaction: { mode: "nearest", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label(context) {
            const point = chartPoints[context.dataIndex];
            const severityLabel = point?.dominantSeverity
              ? `Severidad dominante: ${point.dominantSeverity.charAt(0).toUpperCase()}${point.dominantSeverity.slice(1)}`
              : null;
            if (showPrices) {
              return [
                `Mes: ${point?.x || "-"}`,
                `Promedio anómalo: ${formatCurrency(context.parsed.y)}`,
                `Anomalías del mes: ${point?.count ?? 0}`,
                `Mínimo / Máximo: ${formatCurrency(point?.min ?? context.parsed.y)} / ${formatCurrency(point?.max ?? context.parsed.y)}`,
                severityLabel,
              ].filter(Boolean);
            }
            return [
              `Mes: ${point?.x || "-"}`,
              `Desvío promedio: ${formatNumber(context.parsed.y)}%`,
              `Anomalías del mes: ${point?.count ?? 0}`,
              `Mínimo / Máximo: ${formatNumber(point?.min ?? context.parsed.y)}% / ${formatNumber(point?.max ?? context.parsed.y)}%`,
              severityLabel,
            ].filter(Boolean);
          },
        },
      },
    },
    scales: {
      x: {
        type: "category",
        grid: { display: false },
        ticks: {
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 10,
        },
      },
      y: {
        title: {
          display: true,
          text: showPrices ? "Precio anómalo mensual" : "Variación anómala mensual %",
        },
        ticks: {
          callback: (value) =>
            showPrices
              ? Number(value).toLocaleString("es-AR", { maximumFractionDigits: 0 })
              : `${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 1 })}%`,
        },
      },
    },
    layout: {
      padding: { top: 8 },
    },
  };

  return (
    <Card className={`h-full ${className}`}>
      <CardContent>
        <SectionHeader
          title="Variaciones bruscas"
          description="Primero elegís el mes con anomalías; después se muestran los precios anómalos exactos de ese mes."
        />
        <Box className="mb-4 flex justify-end">
          <Button variant="outlined" size="small" onClick={() => setGlossaryOpen(true)} sx={{ fontWeight: 800 }}>
            Abrir glosario
          </Button>
        </Box>
        <GlossaryDialog open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
        {anomalyInterval ? (
          <Box className="mb-3 flex flex-wrap items-center gap-2">
            <Chip
              label={`Intervalo visible: ${anomalyInterval.firstLabel} → ${anomalyInterval.lastLabel}`}
              size="small"
              variant="outlined"
              sx={{ fontWeight: 800 }}
            />
            <Chip
              label={`${chartPoints.length} meses con anomalías`}
              size="small"
              sx={{ fontWeight: 800, backgroundColor: "#F8FAFC" }}
              variant="outlined"
            />
            {selectedMonthData ? (
              <Chip
                label={`Mes seleccionado: ${selectedMonthData.label}`}
                size="small"
                sx={{ fontWeight: 800, backgroundColor: "#EEF2FF", color: "#4338CA" }}
                variant="outlined"
              />
            ) : null}
          </Box>
        ) : null}
        {seriesError ? <Alert severity="warning">No fue posible cargar las observaciones para anomalías: {seriesError}</Alert> : null}
        {seriesLoading ? (
          <Box className="mb-5 flex h-[340px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600">
            Cargando observaciones para anomalías...
          </Box>
        ) : chartPoints.length ? (
          <Box className="chart-shell anomaly-chart-shell mb-5 h-[340px]">
            <Bar
              ref={chartRef}
              data={chartData}
              options={chartOptions}
              onClick={(event) => {
                const chart = chartRef.current;
                if (!chart) return;
                const elements = getElementAtEvent(chart, event);
                if (!elements.length) return;
                const index = elements[0].index;
                const point = chartPoints[index];
                if (point) setSelectedMonthKey(point.monthKey);
              }}
              redraw
            />
          </Box>
        ) : (
          <Box className="mb-5 flex h-[340px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 px-4 text-center text-sm text-slate-600">
            No hay anomalías para el filtro seleccionado.
          </Box>
        )}
        <Box className="mb-4 flex flex-wrap gap-2">
          {severityFilters.map((filter) => (
            <Button
              key={filter.value}
              size="small"
              variant={severityFilter === filter.value ? "contained" : "outlined"}
              onClick={() => setSeverityFilter(filter.value)}
              sx={{ fontWeight: 800 }}
            >
              {filter.label}
            </Button>
          ))}
        </Box>
        {!selectedMonthData ? (
          <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
            Seleccioná un mes del gráfico para ver sus anomalías exactas.
          </Box>
        ) : !selectedMonthAnomalies.length ? (
          <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
            No hay anomalías para el mes seleccionado.
          </Box>
        ) : (
          <Box className="grid gap-3 xl:grid-cols-2">
            {selectedMonthAnomalies.map((point) => {
              const parsedMotivo = parseAnomalyMotivo(point.motivo_anomalia);
              const expectedRangeVisible =
                point.precio_esperado_anomalia !== null &&
                point.precio_esperado_anomalia !== undefined &&
                point.rango_esperado_min_anomalia !== null &&
                point.rango_esperado_min_anomalia !== undefined &&
                point.rango_esperado_max_anomalia !== null &&
                point.rango_esperado_max_anomalia !== undefined;
              return (
                <Box
                  key={point.observacion_id ?? point.fecha}
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
                          Fecha detectada
                        </Typography>
                        <Typography variant="h4" lineHeight={1.1}>
                          {point.fecha}
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
                      {point.tipo_anomalia ? (
                        <Chip
                          label={formatAnomalyType(point.tipo_anomalia)}
                          size="small"
                          variant="outlined"
                          sx={{ fontWeight: 800, backgroundColor: "#FFFFFF" }}
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

                    <Accordion
                      disableGutters
                      elevation={0}
                      className="mt-3 overflow-hidden rounded-lg border border-slate-200"
                      sx={{ "&:before": { display: "none" } }}
                    >
                      <AccordionSummary expandIcon={<Typography color="text.secondary">⌄</Typography>} sx={{ bgcolor: "#F8FAFC" }}>
                        <Box>
                          <Typography variant="body2" fontWeight={900}>
                            Cómo llegó el modelo a esta alerta
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Ver explicación, señales y valores de referencia
                          </Typography>
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails sx={{ p: 2 }}>
                        <Box component="ul" className="m-0 grid gap-2 pl-5 text-sm text-slate-700">
                          <li>
                            <strong>Lectura principal:</strong> {point.explicacion_anomalia || parsedMotivo.summary}
                          </li>
                          <li>
                            <strong>Clasificación:</strong> {formatAnomalyType(point.tipo_anomalia || "mixta")} · severidad {severityConfig[point.severidad_anomalia]?.label?.toLowerCase() || "sin definir"}.
                          </li>
                          {point.score_anomalia !== null && point.score_anomalia !== undefined ? (
                            <li><strong>Fuerza de la evidencia:</strong> activó un score de {point.score_anomalia}/4{point.confianza_anomalia !== null && point.confianza_anomalia !== undefined ? `, con ${formatPercent(point.confianza_anomalia)} de confianza` : ""}.</li>
                          ) : null}
                          {parsedMotivo.signals.map((signal) => (
                            <li key={`${signal.label}-${signal.detail}`}>
                              <strong>{signal.label}:</strong> {signal.detail || "señal detectada por encima del comportamiento esperado."}
                            </li>
                          ))}
                        </Box>

                        {expectedRangeVisible ? (
                          <Box className="mt-4 grid gap-2 sm:grid-cols-3">
                            <MetricTile
                              label="Precio esperado"
                              value={formatCurrency(getDisplayPrice(point.precio_esperado_anomalia, selectedMaterial?.nombre, point.unidad_base))}
                              helper="Estimación del Random Forest"
                            />
                            <MetricTile
                              label="Rango considerado normal"
                              value={`${formatCurrency(getDisplayPrice(point.rango_esperado_min_anomalia, selectedMaterial?.nombre, point.unidad_base))} a ${formatCurrency(getDisplayPrice(point.rango_esperado_max_anomalia, selectedMaterial?.nombre, point.unidad_base))}`}
                              helper={`Límite dinámico ${formatPercent(point.limite_residuo_anomalia_pct)}`}
                            />
                            <MetricTile
                              label="Distancia observada"
                              value={formatPercent(point.residuo_anomalia_pct)}
                              helper="Residuo frente al precio esperado"
                            />
                          </Box>
                        ) : null}

                        {point.variables_relevantes_anomalia?.length ? (
                          <Box className="mt-4">
                            <Typography color="text.secondary" variant="caption" fontWeight={900}>
                              VARIABLES QUE MÁS INFLUYERON
                            </Typography>
                            <Box className="mt-2 flex flex-wrap gap-1.5">
                              {point.variables_relevantes_anomalia.map((variable) => (
                                <Chip key={variable} label={variable} size="small" variant="outlined" sx={{ backgroundColor: "#F8FAFC" }} />
                              ))}
                            </Box>
                          </Box>
                        ) : null}
                      </AccordionDetails>
                    </Accordion>
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
              Pegá una fecha por línea, o separalas con comas. La evaluación usa el rango visible {firstDate && lastDate ? `${firstDate} a ${lastDate}` : "del historial actual"}.
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

              <Box className="mt-4">
                <Typography variant="h4">Comparación contra baseline</Typography>
                <Typography color="text.secondary" variant="body2" mt={0.5}>
                  Regla simple: marcar cualquier observación cuya variación supere el umbral fijo.
                </Typography>
              </Box>

              <Box className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {baselineSummary.map((item) => (
                  <MetricTile key={`baseline-${item.label}`} label={item.label} value={item.value} helper={item.helper} />
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

              <Box className="mt-3 grid gap-3 lg:grid-cols-2">
                <DetailList title="Fechas baseline" values={evaluation.baseline_fechas_detectadas} emptyText="El baseline no marcó anomalías en el rango." />
                <DetailList title="Fechas confirmadas" values={evaluation.fechas_confirmadas} emptyText="No se cargaron fechas confirmadas." />
              </Box>
            </Box>
          ) : (
            <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
              Cargá fechas confirmadas para medir qué tan preciso está el detector frente a anomalías reales.
            </Box>
          )}

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

function GlossaryDialog({ open, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" scroll="paper">
      <DialogTitle sx={{ pb: 1 }}>
        <Typography variant="h3">Glosario de anomalías</Typography>
        <Typography color="text.secondary" variant="body2" mt={0.5}>
          Una guía rápida para interpretar las alertas y las métricas del detector.
        </Typography>
      </DialogTitle>
      <DialogContent dividers>
        <Box className="grid gap-3 sm:grid-cols-2">
          {GLOSSARY_ITEMS.map(([term, definition]) => (
            <GlossaryItem key={term} term={term} definition={definition} />
          ))}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} variant="contained">Cerrar</Button>
      </DialogActions>
    </Dialog>
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

function formatAnomalyType(value) {
  const labels = {
    cambio_sostenido: "Cambio sostenido",
    desvio_estacional: "Desvío estacional",
    salto_puntual: "Salto puntual",
    desvio_tendencia: "Desvío de tendencia",
    residuo_extremo: "Residuo extremo",
    mixta: "Señal mixta",
  };
  return labels[value] || String(value).replaceAll("_", " ");
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
  const readableSignals = signals.map((signal) => humanizeAnomalySignal(signal));

  return {
    summary:
      parts[0] && parts.length > 1
        ? `${parts[0]}: ${readableSignals.length ? readableSignals[0].label : humanizeAnomalySignal(summary.split(";")[0].trim()).label}`
        : humanizeAnomalySignal(summary).label,
    signals: readableSignals,
  };
}

function humanizeAnomalySignal(signal) {
  const text = String(signal || "").trim();
  const lower = text.toLowerCase();

  if (lower.startsWith("residuo ")) {
    return {
      label: "Residuo alto",
      detail: text.replace(/^residuo\s*/i, "").replaceAll("limite", "límite"),
    };
  }
  if (lower.startsWith("variacion mensual ")) {
    return {
      label: "Salto mensual fuerte",
      detail: text.replace(/^variacion mensual\s*/i, "").replaceAll("limite", "límite").replaceAll("variacion", "variación"),
    };
  }
  if (lower.startsWith("gap estacional ")) {
    return {
      label: "Desvío estacional",
      detail: text.replace(/^gap estacional\s*/i, "").replaceAll("limite", "límite"),
    };
  }
  if (lower.startsWith("desvio de tendencia ")) {
    return {
      label: "Desvío de tendencia",
      detail: text.replace(/^desvio de tendencia\s*/i, "").replaceAll("limite", "límite").replaceAll("desvio", "desvío"),
    };
  }
  if (lower.startsWith("precio esperado ")) {
    return {
      label: "Precio esperado",
      detail: text,
    };
  }
  return {
    label: text
      .replaceAll("desvio", "desvío")
      .replaceAll("variacion", "variación")
      .replaceAll("limite", "límite"),
    detail: "",
  };
}

function severityColor(severity, severityConfig) {
  return severityConfig[severity]?.color || "#CBD5E1";
}
