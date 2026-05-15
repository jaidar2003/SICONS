import { Box, Card, CardContent, Chip, Typography } from "@mui/material";
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
import { Line } from "react-chartjs-2";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber, formatPercentChange, variationTone } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export function AnomaliesCard({ serie, showPrices, selectedMaterial, className = "" }) {
  const anomalies = serie.filter((point) => point.es_anomalia);
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, serie[0]?.unidad_base);
  const labels = serie.map((point) => point.fecha.slice(0, 7));
  const mainSeries = showPrices
    ? serie.map((point) => getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))
    : serie.map((point) => Number(point.variacion_porcentual_anterior || 0));
  const anomalySeries = serie.map((point, index) => (point.es_anomalia ? mainSeries[index] : null));
  const chartLabel = showPrices ? presentation.primaryPriceLabel : "Variacion mensual %";
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
