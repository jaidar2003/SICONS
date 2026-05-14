import CalendarMonthIconModule from "@mui/icons-material/CalendarMonth";
import SavingsOutlinedIconModule from "@mui/icons-material/SavingsOutlined";
import TrendingUpIconModule from "@mui/icons-material/TrendingUp";
import { Alert, Box, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import dayjs from "dayjs";
import { useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { resolveMuiIcon } from "../../shared/components/resolveMuiIcon.js";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { ForecastModelDetails } from "./ForecastModelDetails.jsx";

const CalendarMonthIcon = resolveMuiIcon(CalendarMonthIconModule);
const SavingsOutlinedIcon = resolveMuiIcon(SavingsOutlinedIconModule);
const TrendingUpIcon = resolveMuiIcon(TrendingUpIconModule);

export function CostProjectionCard({ forecast, selectedMaterial, showPrices }) {
  const [quantityInput, setQuantityInput] = useState("100");

  const quantity = Number(quantityInput);
  const isValidQuantity = Number.isFinite(quantity) && quantity > 0;
  const unit = forecast?.unidad_base || selectedMaterial?.unidad_base || "unidad";
  const currentUnitPrice = forecast ? Number(forecast.ultimo_precio_observado) : 0;
  const selection = forecast?.seleccion_modelo || null;

  const scenarios = useMemo(() => {
    if (!forecast || !isValidQuantity) return [];

    const currentCost = currentUnitPrice * quantity;
    return forecast.puntos.map((point) => {
      const projectedUnitPrice = Number(point.precio_proyectado);
      const projectedCost = projectedUnitPrice * quantity;
      const delta = projectedCost - currentCost;
      const deltaPercent = currentCost === 0 ? 0 : (delta / currentCost) * 100;
      return {
        fecha: point.fecha,
        projectedUnitPrice,
        projectedCost,
        delta,
        deltaPercent,
      };
    });
  }, [currentUnitPrice, forecast, isValidQuantity, quantity]);

  const summary = useMemo(() => {
    if (!scenarios.length) return null;

    const cheapestScenario = scenarios.reduce((best, current) => (current.projectedCost < best.projectedCost ? current : best), scenarios[0]);
    const mostExpensiveScenario = scenarios.reduce((worst, current) => (current.projectedCost > worst.projectedCost ? current : worst), scenarios[0]);
    const averageProjectedCost = scenarios.reduce((total, current) => total + current.projectedCost, 0) / scenarios.length;
    const decision = cheapestScenario.delta > 0 ? "Comprar ahora" : "Podés esperar";
    const decisionTone = cheapestScenario.delta > 0 ? "error.main" : "success.main";
    const decisionDetail =
      cheapestScenario.delta > 0
        ? `Anticipar la compra evita al menos ${formatCurrency(cheapestScenario.delta)} frente al mejor horizonte proyectado.`
        : `El mejor horizonte proyectado ahorra ${formatCurrency(Math.abs(cheapestScenario.delta))} frente a comprar hoy.`;

    return {
      currentCost: currentUnitPrice * quantity,
      cheapestScenario,
      mostExpensiveScenario,
      averageProjectedCost,
      decision,
      decisionTone,
      decisionDetail,
    };
  }, [currentUnitPrice, quantity, scenarios]);

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
        <SectionHeader
          title="Proyeccion de costos de obra"
          description="Compara el costo actual con el costo futuro estimado segun la cantidad requerida."
        />
          <Alert severity="info">Activá la vista de precios para proyectar costos a partir del forecast unitario.</Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Proyeccion de costos de obra"
          description="Convertí la cantidad que necesitás en una decisión simple: comprar ahora o esperar."
        />

        {!forecast ? (
          <Alert severity="info">Necesitás un forecast disponible para proyectar costos de compra.</Alert>
        ) : (
          <Stack spacing={3}>
            {!isValidQuantity ? (
              <>
                <Box className="grid gap-4 md:grid-cols-[280px_1fr]">
                  <TextField
                    label={`Cantidad requerida (${unit})`}
                    type="number"
                    value={quantityInput}
                    onChange={(event) => setQuantityInput(event.target.value)}
                    inputProps={{ min: 0, step: "any" }}
                    helperText="Ingresá una cantidad mayor a cero."
                  />
                  <Alert severity="warning">La cantidad requerida debe ser mayor a cero.</Alert>
                </Box>
              </>
            ) : (
              <>
                <Box className="grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 lg:grid-cols-[minmax(240px,.75fr)_minmax(0,1.25fr)] lg:items-stretch">
                  <Box className="rounded-xl border border-slate-200 bg-white p-4 md:p-5">
                    <Typography color="text.secondary" fontSize={12} fontWeight={900} letterSpacing={0} lineHeight={1.2}>
                      Cantidad para esta compra
                    </Typography>
                    <TextField
                      className="mt-4"
                      fullWidth
                      aria-label={`Cantidad (${unit})`}
                      placeholder={`Cantidad (${unit})`}
                      type="number"
                      value={quantityInput}
                      onChange={(event) => setQuantityInput(event.target.value)}
                      inputProps={{ min: 0, step: "any" }}
                      sx={{
                        "& .MuiInputBase-root": {
                          minHeight: 48,
                        },
                      }}
                    />
                    <Typography color="text.secondary" fontSize={13} mt={2} lineHeight={1.5}>
                      Precio actual: {formatCurrency(currentUnitPrice)} por {unit}.
                    </Typography>
                  </Box>

                  <Box className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-[1fr_auto] md:items-center">
                    <Box>
                      <Typography color="text.secondary" fontSize={12} fontWeight={800}>
                        Lectura rápida
                      </Typography>
                      <Typography component="strong" display="block" mt={0.75} fontSize={34} fontWeight={900} lineHeight={1.05} color={summary.decisionTone}>
                        {summary.decision}
                      </Typography>
                      <Typography color="text.secondary" fontSize={14} mt={1}>
                        {summary.decisionDetail}
                      </Typography>
                    </Box>
                    <Box className="rounded-xl bg-slate-50 p-3 md:min-w-[220px]">
                      <Typography color="text.secondary" fontSize={12} fontWeight={800}>
                        Comprar hoy
                      </Typography>
                      <Typography component="strong" display="block" mt={0.75} fontSize={26} fontWeight={900}>
                        {formatCurrency(summary.currentCost)}
                      </Typography>
                      <Typography color="text.secondary" fontSize={13} mt={0.5}>
                        {formatNumber(quantity, 0)} {unit} para {selectedMaterial?.nombre || "el material seleccionado"}.
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                <Box className="grid gap-4 md:grid-cols-3">
                  <SummaryMini
                    icon={<SavingsOutlinedIcon fontSize="small" />}
                    label="Mejor momento para esperar"
                    value={dayjs(summary.cheapestScenario.fecha).format("MMM YY")}
                    helper={formatCurrency(summary.cheapestScenario.projectedCost)}
                  />
                  <SummaryMini
                    icon={<TrendingUpIcon fontSize="small" />}
                    label="Mayor costo proyectado"
                    value={dayjs(summary.mostExpensiveScenario.fecha).format("MMM YY")}
                    helper={formatCurrency(summary.mostExpensiveScenario.projectedCost)}
                  />
                  <SummaryMini
                    icon={<CalendarMonthIcon fontSize="small" />}
                    label="Promedio si esperás"
                    value={formatCurrency(summary.averageProjectedCost)}
                    helper="Entre los horizontes disponibles"
                  />
                </Box>

                <Alert severity="info">
                  Usá esta lectura como apoyo táctico: compara el costo de comprar hoy contra los horizontes del forecast para esta cantidad.
                </Alert>

                <Box className="grid gap-4 md:grid-cols-3">
                  {scenarios.map((scenario) => (
                    <Box key={scenario.fecha} className="rounded-xl border border-slate-200 p-3">
                      <Typography fontSize={12} fontWeight={800} color="text.secondary">
                        Si comprás en {dayjs(scenario.fecha).format("MMM YY")}
                      </Typography>
                      <Typography component="strong" display="block" mt={1} fontSize={22} fontWeight={800}>
                        {formatCurrency(scenario.projectedCost)}
                      </Typography>
                      <Typography color="text.secondary" fontSize={13}>
                        {formatCurrency(scenario.projectedUnitPrice)} por {unit}
                      </Typography>
                      <Typography mt={1.25} fontSize={13} color={scenario.delta >= 0 ? "error.main" : "success.main"} fontWeight={700}>
                        {scenario.delta >= 0 ? "Impacto vs compra actual" : "Ahorro vs compra actual"}: {formatCurrency(Math.abs(scenario.delta))}
                      </Typography>
                      <Typography color="text.secondary" fontSize={13} mt={0.5}>
                        Variacion: {formatNumber(scenario.deltaPercent)}%
                      </Typography>
                    </Box>
                  ))}
                </Box>

                <ForecastModelDetails selection={selection} title="Modelo usado para estimar" compact />
              </>
            )}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryMini({ icon, label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 p-3">
      <Box className="flex items-center gap-2">
        {icon ? <Box className="text-primary">{icon}</Box> : null}
        <Typography color="text.secondary" fontSize={12} fontWeight={800}>
          {label}
        </Typography>
      </Box>
      <Typography component="strong" display="block" mt={0.75} fontSize={22} fontWeight={800} lineHeight={1.1}>
        {value}
      </Typography>
      <Typography color="text.secondary" fontSize={13} mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
