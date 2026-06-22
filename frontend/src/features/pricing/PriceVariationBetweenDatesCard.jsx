import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, Typography } from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber, toApiDate, variationTone } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";
import { fetchPriceVariationBetweenDates } from "./pricing.api.js";

export function PriceVariationBetweenDatesCard({ selectedMaterial, serie, token, showPrices, className = "mt-3" }) {
  const [fechaDesde, setFechaDesde] = useState(null);
  const [fechaHasta, setFechaHasta] = useState(null);
  const [variation, setVariation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const firstDate = serie[0]?.fecha || "";
  const lastDate = serie[serie.length - 1]?.fecha || "";
  const presentation = useMemo(
    () => getMaterialPresentation(selectedMaterial?.nombre, selectedMaterial?.unidad_base),
    [selectedMaterial?.nombre, selectedMaterial?.unidad_base]
  );

  useEffect(() => {
    setFechaDesde(firstDate ? dayjs(firstDate) : null);
    setFechaHasta(lastDate ? dayjs(lastDate) : null);
    setVariation(null);
    setError("");
  }, [firstDate, lastDate, selectedMaterial?.id]);

  async function handleCalculate() {
    setError("");
    setVariation(null);

    if (!selectedMaterial?.id) {
      setError("Seleccioná un material.");
      return;
    }

    if (!fechaDesde || !fechaHasta) {
      setError("Elegí fecha inicial y fecha final.");
      return;
    }

    setLoading(true);
    try {
      const result = await fetchPriceVariationBetweenDates({
        materialId: selectedMaterial.id,
        fechaDesde: toApiDate(fechaDesde),
        fechaHasta: toApiDate(fechaHasta),
        token,
      });
      setVariation(result);
    } catch (variationError) {
      setError(variationError.message);
    } finally {
      setLoading(false);
    }
  }

  if (!showPrices) {
    return (
      <Card className={className}>
        <CardContent>
          <SectionHeader
            title="Variación entre fechas"
            description="Compara dos puntos arbitrarios del historial del material."
          />
          <Alert severity="info">Activá la vista de precios para calcular variaciones entre fechas.</Alert>
        </CardContent>
      </Card>
    );
  }

  const usedDifferentDates =
    variation &&
    (variation.fecha_desde_solicitada !== variation.fecha_desde_usada ||
      variation.fecha_hasta_solicitada !== variation.fecha_hasta_usada);

  return (
    <Card className={className}>
      <CardContent>
        <SectionHeader
          title="Variación entre fechas"
          description="Elegí dos fechas y compará el precio usado por el sistema con variación porcentual."
        />

        <Stack spacing={2.5}>
          <Box className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <DatePicker
              label="Fecha inicial"
              value={fechaDesde}
              maxDate={fechaHasta || undefined}
              onChange={setFechaDesde}
              format="DD/MM/YY"
              slotProps={{ textField: { size: "small" } }}
            />
            <DatePicker
              label="Fecha final"
              value={fechaHasta}
              minDate={fechaDesde || undefined}
              onChange={setFechaHasta}
              format="DD/MM/YY"
              slotProps={{ textField: { size: "small" } }}
            />
            <Button variant="contained" onClick={handleCalculate} disabled={loading || !selectedMaterial?.id}>
              {loading ? "Calculando..." : "Calcular variación"}
            </Button>
          </Box>

          {error ? <Alert severity="error">{error}</Alert> : null}
          {loading ? (
            <Box className="flex justify-center py-2">
              <CircularProgress size={24} />
            </Box>
          ) : null}

          {variation ? (
            <Box className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              <Box className="grid gap-3 md:grid-cols-3">
                <SummaryMini
                  label="Variación"
                  value={`${Number(variation.variacion_porcentual) >= 0 ? "+" : ""}${formatNumber(variation.variacion_porcentual)}%`}
                  helper={`${variation.fecha_desde_usada} a ${variation.fecha_hasta_usada}`}
                  color={variationTone(variation.variacion_porcentual)}
                />
                <SummaryMini
                  label="Precio inicial"
                  value={formatCurrency(getDisplayPrice(variation.precio_desde, selectedMaterial?.nombre, variation.unidad_base))}
                  helper={`${presentation.tablePriceLabel} · ${variation.fecha_desde_usada}`}
                />
                <SummaryMini
                  label="Precio final"
                  value={formatCurrency(getDisplayPrice(variation.precio_hasta, selectedMaterial?.nombre, variation.unidad_base))}
                  helper={`${presentation.tablePriceLabel} · ${variation.fecha_hasta_usada}`}
                />
              </Box>

              {usedDifferentDates ? (
                <Alert severity="warning">
                  El sistema usó las fechas con precio disponible más cercanas dentro de la serie:
                  {" "}
                  {variation.fecha_desde_usada}
                  {" "}
                  y
                  {" "}
                  {variation.fecha_hasta_usada}
                  .
                </Alert>
              ) : (
                <Alert severity="info">La comparación usó exactamente las fechas solicitadas.</Alert>
              )}
            </Box>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

function SummaryMini({ label, value, helper, color = "text.primary" }) {
  return (
    <Box className="rounded-xl border border-slate-200 p-3">
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1} color={color}>
        {value}
      </Typography>
      <Typography color="text.secondary" variant="body2" mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
