import { Alert, Box, Button, ButtonGroup, Card, CardContent, Stack, Typography } from "@mui/material";
import dayjs from "dayjs";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { ForecastModelDetails } from "./ForecastModelDetails.jsx";
import { getModelDisplayName } from "./forecastModelLabels.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

export function ForecastCard({ forecast, serie, horizonteMeses, onChangeHorizon, showPrices }) {
  const baseValue = serie.length ? Number(serie[0].precio_promedio_normalizado) : 0;
  const lastObservedValue = forecast ? Number(forecast.ultimo_precio_observado) : 0;
  const presentation = getMaterialPresentation(forecast?.material_nombre, forecast?.unidad_base);
  const selection = forecast?.seleccion_modelo || null;
  const nextForecastPoint = forecast?.puntos?.[0] || null;
  const displayLastObserved = forecast ? getDisplayPrice(forecast.ultimo_precio_observado, forecast.material_nombre, forecast.unidad_base) : 0;
  const estimatedMonthlyVariation =
    nextForecastPoint && lastObservedValue > 0 ? ((Number(nextForecastPoint.precio_proyectado) - lastObservedValue) / lastObservedValue) * 100 : 0;

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Forecast mensual"
          description="Proyeccion mensual con metricas de fiabilidad obtenidas por backtesting temporal."
          badge={`Horizonte ${horizonteMeses} meses`}
          action={
            <ButtonGroup size="small" variant="outlined">
              {[3, 6, 12].map((value) => (
                <Button key={value} variant={value === horizonteMeses ? "contained" : "outlined"} onClick={() => onChangeHorizon(value)}>
                  {value}m
                </Button>
              ))}
            </ButtonGroup>
          }
        />

        {!forecast ? (
          <Alert severity="info">Seleccioná un material con serie mensual suficiente para ver el forecast.</Alert>
        ) : (
          <Stack spacing={2.5}>
            <Box className="grid gap-3 md:grid-cols-4">
              <MetricMini label="MAPE" value={`${formatNumber(forecast.metricas.mape)}%`} helper={`Backtesting ${forecast.horizonte_meses} meses`} />
              <MetricMini label={showPrices ? "MAE" : "Folds"} value={showPrices ? formatNumber(forecast.metricas.mae) : String(forecast.metricas.folds)} helper={showPrices ? `${forecast.metricas.folds} folds` : "Backtesting temporal"} />
              <MetricMini label="Efectividad" value={`${formatNumber(forecast.metricas.efectividad_informal)}%`} helper="100 - MAPE" />
              <MetricMini
                label={showPrices ? presentation.primaryPriceLabel : "Modelo"}
                value={showPrices ? `${formatCurrency(displayLastObserved)}` : getModelDisplayName(forecast.modelo)}
                helper={
                  showPrices
                    ? `${presentation.displayUnitLabel} · ${dayjs(forecast.ultima_fecha_observada).format("DD/MM/YY")}`
                    : dayjs(forecast.ultima_fecha_observada).format("DD/MM/YY")
                }
              />
            </Box>

            <ForecastModelDetails selection={selection} title="Detalles del modelo" compact />

            {showPrices && nextForecastPoint ? (
              <Box className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
              <MetricMini
                label="Precio proyectado"
                value={formatCurrency(getDisplayPrice(nextForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base))}
                  helper={`Primer mes proyectado: ${dayjs(nextForecastPoint.fecha).format("DD/MM/YY")}`}
                />
                <MetricMini
                  label="Variación mensual estimada"
                  value={`${formatNumber(estimatedMonthlyVariation)}%`}
                  helper={`Vs último observado ${dayjs(forecast.ultima_fecha_observada).format("DD/MM/YY")}`}
                />
              </Box>
            ) : null}

            <Alert severity="info">
              La fiabilidad se interpreta principalmente con `MAPE`. `MAE`, cantidad de folds y efectividad informal complementan la lectura del resultado.
            </Alert>

            <Alert severity="warning">{forecast.supuesto_regresores}</Alert>

              <Box className="grid gap-2 md:grid-cols-3">
                {forecast.puntos.map((punto) => (
                  <Box key={punto.fecha} className="rounded-xl border border-slate-200 p-3">
                  <Typography variant="body2" fontWeight={800} color="text.secondary">
                    {dayjs(punto.fecha).format("DD/MM/YY")}
                  </Typography>
                      {showPrices ? (
                        <>
                          <Typography component="strong" display="block" mt={1} variant="h2" lineHeight={1.1}>
                            {formatCurrency(getDisplayPrice(punto.precio_proyectado, forecast.material_nombre, forecast.unidad_base))}
                          </Typography>
                          <Typography color="text.secondary" variant="body2">
                            {presentation.displayUnitLabel}
                          </Typography>
                        </>
                  ) : (
                    <>
                      <Typography component="strong" display="block" mt={1} variant="h2" lineHeight={1.1}>
                        {`${formatNumber(baseValue === 0 ? 0 : ((Number(punto.precio_proyectado) - baseValue) / baseValue) * 100)}%`}
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        variacion acumulada proyectada
                      </Typography>
                      <Typography color="text.secondary" variant="body2" mt={0.75}>
                        {`Cambio vs ultimo observado: ${formatNumber(lastObservedValue === 0 ? 0 : ((Number(punto.precio_proyectado) - lastObservedValue) / lastObservedValue) * 100)}%`}
                      </Typography>
                    </>
                  )}
                </Box>
              ))}
            </Box>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

function MetricMini({ label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 p-3">
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
        {value}
      </Typography>
      <Typography color="text.secondary" variant="body2" mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
