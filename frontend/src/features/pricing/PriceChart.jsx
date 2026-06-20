import { Alert, Card, CardContent } from "@mui/material";
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
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export function PriceChart({
  serie,
  forecast,
  selectedMaterial,
  action,
  showPrices,
  className = "",
  chartMode = "base",
  commercialMarginPct = null,
  canShowCostDetails = true,
}) {
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, selectedMaterial?.unidad_base);
  const showBagEquivalents = presentation.type === "cement" && serie.some((point) => point.precio_equivalente_25kg !== null);
  const baseValue = serie.length ? Number(serie[0].precio_promedio_normalizado) : 0;
  const lastObservedValue = serie.length ? Number(serie[serie.length - 1].precio_promedio_normalizado) : 0;
  const commercialMarginNumber = Number(commercialMarginPct);
  const hasCommercialMargin = Number.isFinite(commercialMarginNumber);
  const commercialMultiplier = hasCommercialMargin ? 1 + commercialMarginNumber / 100 : 1;
  const variationSeries = serie.map((point) =>
    baseValue === 0 ? 0 : ((Number(point.precio_promedio_normalizado) - baseValue) / baseValue) * 100
  );
  const forecastPoints = forecast?.puntos ?? [];
  const labels = [...serie.map((point) => point.fecha), ...forecastPoints.map((point) => point.fecha.slice(0, 7))];
  const projectedVariationSeries = forecastPoints.map((point) =>
    baseValue === 0 ? 0 : ((Number(point.precio_proyectado) - baseValue) / baseValue) * 100
  );
  const projectedVariationVsLastObserved = forecastPoints.map((point) =>
    lastObservedValue === 0 ? 0 : ((Number(point.precio_proyectado) - lastObservedValue) / lastObservedValue) * 100
  );
  const historicalDataset = showPrices
    ? serie.map((point) => getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))
    : variationSeries;
  const forecastDataset = showPrices
    ? forecastPoints.map((point) => getDisplayPrice(point.precio_proyectado, selectedMaterial?.nombre, forecast?.unidad_base))
    : projectedVariationSeries;
  const optimisticForecastDataset = showPrices
    ? forecastPoints.map((point) => getDisplayPrice(point.precio_optimista ?? point.precio_proyectado, selectedMaterial?.nombre, forecast?.unidad_base))
    : forecastPoints.map((point) =>
        baseValue === 0 ? 0 : ((Number(point.precio_optimista ?? point.precio_proyectado) - baseValue) / baseValue) * 100
      );
  const pessimisticForecastDataset = showPrices
    ? forecastPoints.map((point) => getDisplayPrice(point.precio_pesimista ?? point.precio_proyectado, selectedMaterial?.nombre, forecast?.unidad_base))
    : forecastPoints.map((point) =>
        baseValue === 0 ? 0 : ((Number(point.precio_pesimista ?? point.precio_proyectado) - baseValue) / baseValue) * 100
      );
  const commercialHistoricalDataset = showPrices
    ? serie.map((point) => getDisplayPrice(Number(point.precio_promedio_normalizado) * commercialMultiplier, selectedMaterial?.nombre, point.unidad_base))
    : variationSeries;
  const commercialForecastDataset = showPrices
    ? forecastPoints.map((point) => getDisplayPrice(Number(point.precio_proyectado) * commercialMultiplier, selectedMaterial?.nombre, forecast?.unidad_base))
    : projectedVariationSeries;
  const forecastLine = [
    ...Array(Math.max(serie.length - 1, 0)).fill(null),
    ...(serie.length ? [historicalDataset[historicalDataset.length - 1]] : []),
    ...forecastDataset,
  ];
  const optimisticForecastLine = [
    ...Array(Math.max(serie.length - 1, 0)).fill(null),
    ...(serie.length ? [historicalDataset[historicalDataset.length - 1]] : []),
    ...optimisticForecastDataset,
  ];
  const pessimisticForecastLine = [
    ...Array(Math.max(serie.length - 1, 0)).fill(null),
    ...(serie.length ? [historicalDataset[historicalDataset.length - 1]] : []),
    ...pessimisticForecastDataset,
  ];
  const commercialForecastLine = [
    ...Array(Math.max(serie.length - 1, 0)).fill(null),
    ...(serie.length ? [commercialHistoricalDataset[commercialHistoricalDataset.length - 1]] : []),
    ...commercialForecastDataset,
  ];
  const baseCombinedLine = [...historicalDataset, ...forecastDataset];
  const commercialCombinedLine = [...commercialHistoricalDataset, ...commercialForecastDataset];

  const chartTitle =
    showPrices && chartMode === "commercial"
      ? "Evolucion historica del precio minorista"
      : showPrices && chartMode === "comparative"
        ? "Costo y precio minorista superpuestos"
        : showPrices
          ? "Evolucion historica del precio normalizado"
          : "Evolucion historica porcentual";
  const forecastBoundaryNote = forecastPoints.length ? " La franja naranja marca el tramo estimado." : "";
  const chartDescription =
    showPrices && chartMode === "commercial"
      ? canShowCostDetails
        ? `Precio minorista derivado del forecast de costo${hasCommercialMargin ? ` con margen ${formatNumber(commercialMarginNumber)}%` : ""}.${forecastBoundaryNote}`
        : `Precio minorista proyectado para el material seleccionado.${forecastBoundaryNote}`
      : showPrices && chartMode === "comparative"
        ? `La curva azul es el precio de costo y la verde el precio minorista.${forecastBoundaryNote}`
        : selectedMaterial
          ? showPrices
            ? `${selectedMaterial.nombre}: ${presentation.primaryPriceLabel.toLowerCase()} en ${presentation.displayUnitLabel}${forecastPoints.length ? " con proyeccion mensual" : ""}.${forecastBoundaryNote}`
            : `${selectedMaterial.nombre}: variacion acumulada respecto del inicio del periodo${forecastPoints.length ? " con forecast proyectado" : ""}.${forecastBoundaryNote}`
          : showPrices
            ? `Precio de referencia del material.${forecastBoundaryNote}`
            : `Variacion acumulada del periodo.${forecastBoundaryNote}`;
  const chartBadge =
    canShowCostDetails && showPrices && chartMode === "commercial" && hasCommercialMargin
      ? `Margen ${formatNumber(commercialMarginNumber)}%`
    : canShowCostDetails && showPrices && chartMode === "comparative" && hasCommercialMargin
        ? "Dos curvas"
        : forecastPoints.length
          ? "Historico + forecast"
          : "Precios mensuales";

  const chartData = (() => {
    if (!showPrices) {
      return {
        labels,
        datasets: [
          {
            label: "Variacion acumulada %",
            data: [...variationSeries, ...Array(forecastPoints.length).fill(null)],
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
                  label: "Forecast acumulado %",
                  data: forecastLine,
                  borderColor: "#ED2939",
                  backgroundColor: "rgba(237, 41, 57, 0.18)",
                  fill: true,
                  borderWidth: 2.5,
                  tension: 0.2,
                  pointRadius: 3,
                  pointHoverRadius: 6,
                  pointBackgroundColor: "#fff7ed",
                  pointBorderColor: "#ED2939",
                  pointBorderWidth: 2,
                  borderDash: [8, 6],
                },
              ]
            : []),
        ],
      };
    }

    if (chartMode === "commercial" && !hasCommercialMargin && !canShowCostDetails) {
      return {
        labels,
        datasets: [],
      };
    }

    if (chartMode === "commercial") {
      return {
        labels,
        datasets: [
          {
            label: "Precio minorista",
            data: [...commercialHistoricalDataset, ...Array(forecastPoints.length).fill(null)],
            borderColor: "#0f766e",
            backgroundColor: "rgba(15, 118, 110, 0.12)",
            fill: true,
            borderWidth: 2.5,
            tension: 0.26,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#ecfdf5",
            pointBorderColor: "#0f766e",
            pointBorderWidth: 2,
          },
          ...(forecastPoints.length
            ? [
                {
                  label: "Forecast minorista",
                  data: commercialForecastLine,
                  borderColor: "#16a34a",
                  backgroundColor: "rgba(22, 163, 74, 0.18)",
                  fill: true,
                  borderWidth: 2.5,
                  tension: 0.2,
                  pointRadius: 3,
                  pointHoverRadius: 6,
                  pointBackgroundColor: "#f0fdf4",
                  pointBorderColor: "#16a34a",
                  pointBorderWidth: 2,
                  borderDash: [8, 6],
                },
              ]
            : []),
        ],
      };
    }

    if (chartMode === "comparative" && hasCommercialMargin) {
      return {
        labels,
        datasets: [
          {
            label: "Precio de costo",
            data: baseCombinedLine,
            borderColor: "#002395",
            backgroundColor: "rgba(0, 35, 149, 0.10)",
            fill: false,
            borderWidth: 2.5,
            tension: 0.22,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#FEFBFF",
            pointBorderColor: "#002395",
            pointBorderWidth: 2,
          },
          {
            label: "Precio minorista",
            data: commercialCombinedLine,
            borderColor: "#0f766e",
            backgroundColor: "rgba(15, 118, 110, 0.10)",
            fill: false,
            borderWidth: 2.5,
            tension: 0.22,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#ecfdf5",
            pointBorderColor: "#0f766e",
            pointBorderWidth: 2,
            borderDash: [8, 6],
          },
        ],
      };
    }

    return {
      labels,
      datasets: [
        {
          label: showPrices ? presentation.chartAxisLabel : "Variacion acumulada %",
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
                label: "Escenario pesimista (alto)",
                data: pessimisticForecastLine,
                borderColor: "transparent",
                backgroundColor: "rgba(237, 41, 57, 0.08)",
                fill: false,
                borderWidth: 0,
                tension: 0.2,
                pointRadius: 0,
              },
              {
                label: "Escenario optimista (bajo)",
                data: optimisticForecastLine,
                borderColor: "transparent",
                backgroundColor: "rgba(237, 41, 57, 0.08)",
                fill: "-1",
                borderWidth: 0,
                tension: 0.2,
                pointRadius: 0,
              },
              {
                label: showPrices ? "Forecast" : "Forecast acumulado %",
                data: forecastLine,
                borderColor: "#ED2939",
                backgroundColor: "transparent",
                fill: false,
                borderWidth: 2.5,
                tension: 0.2,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: "#fff7ed",
                pointBorderColor: "#ED2939",
                pointBorderWidth: 2,
                borderDash: [8, 6],
              },
            ]
          : []),
      ],
    };
  })();

  function isForecastDatasetLabel(label) {
    return label === "Forecast acumulado %" || label === "Forecast" || label === "Forecast minorista";
  }

  function getCommercialTooltipLines(point, label) {
    if (!showPrices) {
      return [`${label}: ${formatNumber(((Number(point.precio_proyectado) * commercialMultiplier - baseValue) / baseValue) * 100)}%`];
    }

    const baseForecast = getDisplayPrice(point.precio_proyectado, selectedMaterial?.nombre, forecast?.unidad_base);
    const commercialForecast = getDisplayPrice(Number(point.precio_proyectado) * commercialMultiplier, selectedMaterial?.nombre, forecast?.unidad_base);
    if (!canShowCostDetails) {
      return [`${label}: ${formatCurrency(commercialForecast)}`];
    }
    const optimisticCommercial = getDisplayPrice(Number(point.precio_optimista) * commercialMultiplier, selectedMaterial?.nombre, forecast?.unidad_base);
    const pessimisticCommercial = getDisplayPrice(Number(point.precio_pesimista) * commercialMultiplier, selectedMaterial?.nombre, forecast?.unidad_base);
    return [
      `${label}: ${formatCurrency(commercialForecast)}`,
      `Base forecast: ${formatCurrency(baseForecast)}`,
      `Optimista: ${formatCurrency(optimisticCommercial)}`,
      `Pesimista: ${formatCurrency(pessimisticCommercial)}`,
    ];
  }

  const forecastBoundaryPlugin = {
    id: "forecast-boundary-marker",
    beforeDatasetsDraw(chart) {
      if (!forecastPoints.length || serie.length === 0) return;
      const xScale = chart.scales.x;
      const { chartArea, ctx } = chart;
      if (!xScale || !chartArea) return;

      const leftPixel = xScale.getPixelForValue(serie.length - 1);
      const rightPixel = xScale.getPixelForValue(serie.length);
      const boundaryX = Math.max(chartArea.left, Math.min(chartArea.right, (leftPixel + rightPixel) / 2));

      ctx.save();
      ctx.fillStyle = "rgba(237, 41, 57, 0.05)";
      ctx.fillRect(boundaryX, chartArea.top, chartArea.right - boundaryX, chartArea.bottom - chartArea.top);
      ctx.restore();
    },
    afterDatasetsDraw(chart) {
      if (!forecastPoints.length || serie.length === 0) return;
      const xScale = chart.scales.x;
      const { chartArea, ctx } = chart;
      if (!xScale || !chartArea) return;

      const leftPixel = xScale.getPixelForValue(serie.length - 1);
      const rightPixel = xScale.getPixelForValue(serie.length);
      const boundaryX = Math.max(chartArea.left, Math.min(chartArea.right, (leftPixel + rightPixel) / 2));

      ctx.save();
      ctx.strokeStyle = "#ED2939";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 6]);
      ctx.beginPath();
      ctx.moveTo(boundaryX, chartArea.top);
      ctx.lineTo(boundaryX, chartArea.bottom);
      ctx.stroke();
      ctx.setLineDash([]);

      const label = "Inicio de estimacion";
      ctx.font = "700 12px Inter, sans-serif";
      const paddingX = 10;
      const labelWidth = ctx.measureText(label).width + paddingX * 2;
      const labelHeight = 24;
      let labelX = boundaryX + 10;
      if (labelX + labelWidth > chartArea.right - 8) {
        labelX = boundaryX - labelWidth - 10;
      }
      labelX = Math.max(chartArea.left + 8, labelX);
      const labelY = chartArea.top + 10;

      ctx.fillStyle = "rgba(255, 241, 242, 0.98)";
      ctx.fillRect(labelX, labelY, labelWidth, labelHeight);
      ctx.strokeStyle = "#ED2939";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(labelX, labelY, labelWidth, labelHeight);
      ctx.fillStyle = "#C81E34";
      ctx.textBaseline = "middle";
      ctx.fillText(label, labelX + paddingX, labelY + labelHeight / 2 + 0.5);
      ctx.restore();
    },
  };

  const options = {
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom" },
      tooltip: {
        callbacks: {
          label(context) {
            const datasetLabel = context.dataset.label || "";
            if (chartMode === "commercial" && datasetLabel === "Precio minorista") {
              return [showPrices ? `${datasetLabel}: ${formatCurrency(context.parsed.y)}` : `${datasetLabel}: ${formatNumber(context.parsed.y)}%`];
            }

            if (chartMode === "commercial" && datasetLabel === "Forecast minorista" && forecastPoints.length) {
              const forecastIndex = context.dataIndex - serie.length;
              if (forecastIndex < 0) {
                return showPrices
                  ? [`Ultimo observado: ${formatCurrency(context.parsed.y)}`]
                  : [`Ultimo observado: ${formatNumber(variationSeries[variationSeries.length - 1])}%`];
              }
              const point = forecastPoints[forecastIndex];
              return getCommercialTooltipLines(point, datasetLabel);
            }

            if (chartMode === "comparative" && datasetLabel === "Precio minorista" && forecastPoints.length) {
              const point = serie[context.dataIndex];
              if (showPrices) {
                return [
                  `Precio minorista: ${formatCurrency(context.parsed.y)}`,
                  `Precio de costo: ${formatCurrency(getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))}`,
                ];
              }
              return [
                `Precio minorista: ${formatNumber(context.parsed.y)}%`,
                `Precio de costo: ${formatNumber(variationSeries[context.dataIndex])}%`,
              ];
            }

            if (forecastPoints.length && isForecastDatasetLabel(datasetLabel)) {
              const forecastIndex = context.dataIndex - serie.length;
              if (forecastIndex < 0) {
                return showPrices
                  ? [`Ultimo observado: ${formatCurrency(context.parsed.y)}`]
                  : [`Ultimo observado: ${formatNumber(variationSeries[variationSeries.length - 1])}%`];
              }
              if (showPrices) {
                const point = forecastPoints[forecastIndex];
                return [
                  `${datasetLabel}: ${formatCurrency(point.precio_proyectado)}`,
                  `Optimista: ${formatCurrency(point.precio_optimista)}`,
                  `Pesimista: ${formatCurrency(point.precio_pesimista)}`,
                ];
              }
              return [
                `${datasetLabel}: ${formatNumber(projectedVariationSeries[forecastIndex])}%`,
                `Variacion vs ultimo observado: ${formatNumber(projectedVariationVsLastObserved[forecastIndex])}%`,
              ];
            }

            const point = serie[context.dataIndex];
            if (showPrices) {
              const publicLines = [
                `${context.dataset.label}: ${formatCurrency(context.parsed.y)}`,
                `Variacion anterior: ${point.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point.variacion_porcentual_anterior)}%`}`,
              ];
              if (!canShowCostDetails) return publicLines;
              return [
                publicLines[0],
                chartMode === "base" && showBagEquivalents ? `25 kg / 50 kg: ${formatCurrency(point.precio_equivalente_25kg)} / ${formatCurrency(point.precio_equivalente_50kg)}` : null,
                `Muestra: ${point.cantidad_registros} ${point.cantidad_registros === 1 ? "precio" : "precios"}`,
                publicLines[1],
                `Fuentes: ${point.fuentes.join(", ") || "-"}`,
              ];
            }
            return [
              `Variacion acumulada: ${formatNumber(variationSeries[context.dataIndex])}%`,
              `Variacion anterior: ${point.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point.variacion_porcentual_anterior)}%`}`,
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
        title: {
          display: true,
          text: showPrices
            ? chartMode === "commercial" && hasCommercialMargin
              ? `${presentation.chartAxisLabel} minorista`
              : chartMode === "comparative" && hasCommercialMargin
                ? presentation.chartAxisLabel
                : presentation.chartAxisLabel
            : "Variacion acumulada %",
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
        <SectionHeader
          title={chartTitle}
          description={chartDescription}
          badge={chartBadge}
          action={action}
        />
        {showPrices && chartMode !== "base" && !hasCommercialMargin ? (
          <Alert severity="warning" className="mb-3">
            {canShowCostDetails
              ? "Sin precio minorista configurado. Se muestra solo el precio de costo."
              : "Sin precio minorista configurado para este material."}
          </Alert>
        ) : null}
        <div className="chart-shell h-[360px]">
          <Line
            key={`${showPrices}-${forecast?.horizonte_meses || 0}-${forecastPoints.length}-${forecastPoints.at(-1)?.fecha || "none"}`}
            data={chartData}
            options={options}
            plugins={[forecastBoundaryPlugin]}
            redraw
          />
        </div>
      </CardContent>
    </Card>
  );
}
