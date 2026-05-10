import { Alert, Box, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { ForecastModelDetails } from "./ForecastModelDetails.jsx";

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

    return {
      currentCost: currentUnitPrice * quantity,
      cheapestScenario,
      mostExpensiveScenario,
      averageProjectedCost,
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
          description="Calcula el costo actual y lo compara contra cada horizonte proyectado para el material seleccionado."
        />

        <Box className="mt-3">
          <ForecastModelDetails selection={selection} title="Detalles del modelo" compact />
        </Box>

        {!forecast ? (
          <Alert severity="info">Necesitás un forecast disponible para proyectar costos de compra.</Alert>
        ) : (
          <Stack spacing={3}>
            <Box className="grid gap-4 md:grid-cols-[280px_1fr]">
              <TextField
                label={`Cantidad requerida (${unit})`}
                type="number"
                value={quantityInput}
                onChange={(event) => setQuantityInput(event.target.value)}
                inputProps={{ min: 0, step: "any" }}
                helperText="Ingresá la cantidad necesaria para estimar el impacto economico futuro."
              />

              <Box className="rounded-xl border border-slate-200 p-3">
                <Typography color="text.secondary" fontSize={12} fontWeight={800}>
                  Costo actual estimado
                </Typography>
                <Typography component="strong" display="block" mt={0.75} fontSize={28} fontWeight={800}>
                  {isValidQuantity ? formatCurrency(currentUnitPrice * quantity) : "-"}
                </Typography>
                <Typography color="text.secondary" fontSize={13} mt={0.5}>
                  {isValidQuantity
                    ? `${formatNumber(quantity, 0)} ${unit} x ${formatCurrency(currentUnitPrice)} por ${unit}`
                    : "Ingresá una cantidad mayor a cero para habilitar la comparacion."}
                </Typography>
              </Box>
            </Box>

            {!isValidQuantity ? (
              <Alert severity="warning">La cantidad requerida debe ser mayor a cero.</Alert>
            ) : (
              <>
                <Box className="grid gap-4 md:grid-cols-4">
                  <SummaryMini
                    label="Mejor escenario"
                    value={summary ? summary.cheapestScenario.fecha : "-"}
                    helper={summary ? formatCurrency(summary.cheapestScenario.projectedCost) : "-"}
                  />
                  <SummaryMini
                    label="Peor escenario"
                    value={summary ? summary.mostExpensiveScenario.fecha : "-"}
                    helper={summary ? formatCurrency(summary.mostExpensiveScenario.projectedCost) : "-"}
                  />
                  <SummaryMini
                    label="Promedio proyectado"
                    value={summary ? formatCurrency(summary.averageProjectedCost) : "-"}
                    helper="Costo medio entre escenarios"
                  />
                  <SummaryMini
                    label="Decision base"
                    value={summary && summary.cheapestScenario.delta > 0 ? "Comprar ahora" : "Esperar"}
                    helper={
                      summary
                        ? summary.cheapestScenario.delta > 0
                          ? `Se evitarian ${formatCurrency(summary.cheapestScenario.delta)} frente al mejor escenario futuro`
                          : `El mejor escenario futuro ahorraria ${formatCurrency(Math.abs(summary.cheapestScenario.delta))}`
                        : "-"
                    }
                  />
                </Box>

                <Alert severity="info">
                  Esta simulacion compara escenarios temporales de compra a partir del forecast unitario. Sirve como apoyo para decisiones tacticas, no como recomendacion definitiva de compra.
                </Alert>

                <Box className="grid gap-4 md:grid-cols-3">
                  {scenarios.map((scenario) => (
                    <Box key={scenario.fecha} className="rounded-xl border border-slate-200 p-3">
                      <Typography fontSize={12} fontWeight={800} color="text.secondary">
                        Horizonte {scenario.fecha}
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
              </>
            )}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryMini({ label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 p-3">
      <Typography color="text.secondary" fontSize={12} fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} fontSize={22} fontWeight={800} lineHeight={1.1}>
        {value}
      </Typography>
      <Typography color="text.secondary" fontSize={13} mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
