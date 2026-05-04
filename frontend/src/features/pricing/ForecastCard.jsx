import { Alert, Box, Button, ButtonGroup, Card, CardContent, Divider, Stack, Typography } from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";

export function ForecastCard({ forecast, serie, horizonteMeses, onChangeHorizon, showPrices }) {
  const baseValue = serie.length ? Number(serie[0].precio_promedio_normalizado) : 0;
  const lastObservedValue = forecast ? Number(forecast.ultimo_precio_observado) : 0;

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Forecast mensual"
          description="Modelo Prophet con dolar oficial y mayorista como regresores externos."
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
                label={showPrices ? "Ultimo observado" : "Modelo"}
                value={showPrices ? `${formatCurrency(forecast.ultimo_precio_observado)} / ${forecast.unidad_base}` : forecast.modelo}
                helper={showPrices ? forecast.ultima_fecha_observada : forecast.ultima_fecha_observada}
              />
            </Box>

            <Alert severity="warning">{forecast.supuesto_regresores}</Alert>

            <Box className="grid gap-2 md:grid-cols-3">
              {forecast.puntos.map((punto) => (
                <Box key={punto.fecha} className="rounded-xl border border-slate-200 p-3">
                  <Typography fontSize={12} fontWeight={800} color="text.secondary">
                    {punto.fecha}
                  </Typography>
                  {showPrices ? (
                    <>
                      <Typography component="strong" display="block" mt={1} fontSize={22} fontWeight={800}>
                        {formatCurrency(punto.precio_proyectado)}
                      </Typography>
                      <Typography color="text.secondary" fontSize={13}>
                        por {forecast.unidad_base}
                      </Typography>
                      {punto.precio_equivalente_25kg !== null ? (
                        <>
                          <Divider className="my-2" />
                          <Typography fontSize={13}>25 kg: {formatCurrency(punto.precio_equivalente_25kg)}</Typography>
                          <Typography fontSize={13}>50 kg: {formatCurrency(punto.precio_equivalente_50kg)}</Typography>
                        </>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <Typography component="strong" display="block" mt={1} fontSize={22} fontWeight={800}>
                        {`${formatNumber(baseValue === 0 ? 0 : ((Number(punto.precio_proyectado) - baseValue) / baseValue) * 100)}%`}
                      </Typography>
                      <Typography color="text.secondary" fontSize={13}>
                        variacion acumulada proyectada
                      </Typography>
                      <Typography color="text.secondary" fontSize={13} mt={0.75}>
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
      <Typography color="text.secondary" fontSize={12} fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} fontSize={26} fontWeight={800} lineHeight={1.1}>
        {value}
      </Typography>
      <Typography color="text.secondary" fontSize={13} mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
