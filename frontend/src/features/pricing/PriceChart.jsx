import { Card, CardContent } from "@mui/material";
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
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export function PriceChart({ serie, forecast, selectedMaterial, action, showPrices }) {
  const baseValue = serie.length ? Number(serie[0].precio_promedio_normalizado) : 0;
  const variationSeries = serie.map((point) =>
    baseValue === 0 ? 0 : ((Number(point.precio_promedio_normalizado) - baseValue) / baseValue) * 100
  );
  const forecastPoints = forecast?.puntos ?? [];
  const labels = [...serie.map((point) => point.fecha.slice(0, 7)), ...forecastPoints.map((point) => point.fecha.slice(0, 7))];
  const projectedValues = forecastPoints.map((point) => Number(point.precio_proyectado));
  const projectedVariationSeries = forecastPoints.map((point) =>
    baseValue === 0 ? 0 : ((Number(point.precio_proyectado) - baseValue) / baseValue) * 100
  );
  const historicalDataset = showPrices
    ? serie.map((point) => Number(point.precio_promedio_normalizado))
    : variationSeries;
  const forecastDataset = showPrices ? projectedValues : projectedVariationSeries;
  const forecastLine = [
    ...Array(Math.max(serie.length - 1, 0)).fill(null),
    ...(serie.length ? [historicalDataset[historicalDataset.length - 1]] : []),
    ...forecastDataset,
  ];

  const data = {
    labels,
    datasets: [
      {
        label: showPrices ? "ARS por kg" : "Variacion acumulada %",
        data: [...historicalDataset, ...Array(forecastPoints.length).fill(null)],
        borderColor: "#002395",
        backgroundColor: "rgba(0, 35, 149, 0.12)",
        fill: true,
        borderWidth: 2.5,
        tension: 0.26,
        pointRadius: 3,
        pointHoverRadius: 6,
        pointBackgroundColor: "#FEFBFF",
        pointBorderColor: "#002395",
        pointBorderWidth: 2,
      },
      ...(forecastPoints.length
        ? [
            {
              label: showPrices ? "Forecast" : "Forecast %",
              data: forecastLine,
              borderColor: "#f97316",
              backgroundColor: "rgba(249, 115, 22, 0.18)",
              fill: true,
              borderWidth: 2.5,
              tension: 0.2,
              pointRadius: 3,
              pointHoverRadius: 6,
              pointBackgroundColor: "#fff7ed",
              pointBorderColor: "#f97316",
              pointBorderWidth: 2,
              borderDash: [8, 6],
            },
          ]
        : []),
    ],
  };

  const options = {
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom" },
      tooltip: {
        callbacks: {
          label(context) {
            if (context.datasetIndex === 1 && forecastPoints.length) {
              const forecastIndex = context.dataIndex - serie.length;
              if (forecastIndex < 0) {
                const lastHistoricalPoint = serie[serie.length - 1];
                return showPrices
                  ? [`Ultimo observado: ${formatCurrency(lastHistoricalPoint.precio_promedio_normalizado)}`]
                  : [`Ultimo observado: ${formatNumber(variationSeries[variationSeries.length - 1])}%`];
              }
              const point = forecastPoints[forecastIndex];
              if (showPrices) {
                return [
                  `Proyeccion/kg: ${formatCurrency(point.precio_proyectado)}`,
                  point.precio_equivalente_25kg !== null ? `25 kg: ${formatCurrency(point.precio_equivalente_25kg)}` : null,
                  point.precio_equivalente_50kg !== null ? `50 kg: ${formatCurrency(point.precio_equivalente_50kg)}` : null,
                ].filter(Boolean);
              }
              return [`Variacion proyectada: ${formatNumber(projectedVariationSeries[forecastIndex])}%`];
            }

            const point = serie[context.dataIndex];
            if (showPrices) {
              return [
                `Precio/kg: ${formatCurrency(point.precio_promedio_normalizado)}`,
                `25 kg: ${formatCurrency(point.precio_equivalente_25kg)}`,
                `50 kg: ${formatCurrency(point.precio_equivalente_50kg)}`,
                `Muestra: ${point.cantidad_registros} ${point.cantidad_registros === 1 ? "precio" : "precios"}`,
                `Variacion mensual: ${point.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point.variacion_porcentual_anterior)}%`}`,
                `Fuentes: ${point.fuentes.join(", ") || "-"}`,
              ];
            }
            return [
              `Variacion acumulada: ${formatNumber(variationSeries[context.dataIndex])}%`,
              `Variacion mensual: ${point.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point.variacion_porcentual_anterior)}%`}`,
              `Muestra: ${point.cantidad_registros} ${point.cantidad_registros === 1 ? "precio" : "precios"}`,
              `Fuentes: ${point.fuentes.join(", ") || "-"}`,
            ];
          },
        },
      },
    },
    scales: {
      x: { grid: { display: false } },
      y: {
        title: { display: true, text: showPrices ? "ARS/kg" : "Variacion %" },
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
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title={showPrices ? "Evolucion historica del precio normalizado" : "Evolucion historica porcentual"}
          description={
            selectedMaterial
              ? showPrices
                ? `${selectedMaterial.nombre}: precio normalizado en ${selectedMaterial.unidad_base}${forecastPoints.length ? " con proyeccion mensual" : ""}`
                : `${selectedMaterial.nombre}: variacion acumulada respecto del inicio del periodo${forecastPoints.length ? " con forecast proyectado" : ""}`
              : showPrices
                ? "ARS por unidad base"
                : "Variacion acumulada del periodo"
          }
          badge={forecastPoints.length ? "Historico + forecast" : "Promedio mensual"}
          action={action}
        />
        <div className="chart-shell h-[360px]">
          <Line
            key={`${showPrices}-${forecast?.horizonte_meses || 0}-${forecastPoints.length}-${forecastPoints.at(-1)?.fecha || "none"}`}
            data={data}
            options={options}
            redraw
          />
        </div>
      </CardContent>
    </Card>
  );
}
