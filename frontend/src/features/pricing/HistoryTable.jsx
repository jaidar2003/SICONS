import { useEffect, useState } from "react";
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Card, CardContent, Chip, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import ExpandMoreIconModule from "@mui/icons-material/ExpandMore";
import dayjs from "dayjs";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { resolveMuiIcon } from "../../shared/components/resolveMuiIcon.js";
import { formatCurrency, formatNumber, toApiDate, variationTone } from "../../shared/utils/formatters.js";
import { fetchSerie } from "./pricing.api.js";
import { getDataOriginPresentation, getNormalizedPriceLabel, getPurchasedPresentationLabel } from "./historyProvenance.js";

const ExpandMoreIcon = resolveMuiIcon(ExpandMoreIconModule);

export function HistoryTable({ serie, showPrices, selectedMaterial, token, desde, hasta, className = "" }) {
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!selectedMaterial?.id || !token) {
      setObservations([]);
      return undefined;
    }

    setLoading(true);
    setError("");
    setObservations([]);
    fetchSerie({
      materialId: selectedMaterial.id,
      desde: toApiDate(desde),
      hasta: toApiDate(hasta),
      agrupacion: "observaciones",
      token,
    })
      .then((result) => {
        if (!cancelled) setObservations(result);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar el detalle de procedencia. Reintentá actualizando el historial.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [desde, hasta, selectedMaterial?.id, token]);

  const unit = observations[0]?.unidad_base || serie[0]?.unidad_base;
  const isCement = selectedMaterial?.nombre?.toLowerCase().includes("cemento");

  return (
    <Card className={`h-full ${className}`}>
      <CardContent>
        <SectionHeader title="Historial de precios" description="Observaciones individuales con su procedencia, presentación comprada y precio comparable." />
        {isCement ? (
          <Alert severity="info" sx={{ mt: 2 }}>
            La presentación comprada corresponde a cada comprobante. Actualmente una bolsa de cemento equivale a 25 kg; el precio normalizado en ARS/kg permite comparar bolsas históricas de 50 kg con las actuales de 25 kg.
          </Alert>
        ) : null}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight={800}>Ver tabla histórica</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {loading ? (
              <Box className="flex justify-center py-8" aria-label="Cargando detalle histórico">
                <CircularProgress size={28} />
              </Box>
            ) : null}
            {error ? <Alert severity="error">{error}</Alert> : null}
            {!loading && !error && observations.length === 0 ? <Alert severity="info">No hay observaciones para el período seleccionado.</Alert> : null}
            {!loading && !error && observations.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell align="center">Fecha</TableCell>
                    <TableCell align="center">Procedencia</TableCell>
                    <TableCell align="center">Presentación comprada</TableCell>
                    {showPrices ? <TableCell align="center">Precio del comprobante</TableCell> : null}
                    {showPrices ? <TableCell align="center">{getNormalizedPriceLabel(unit)}</TableCell> : null}
                    <TableCell align="center">Variación</TableCell>
                    <TableCell align="center">Fuente</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {observations.map((point, index) => {
                    const origin = getDataOriginPresentation(point);
                    return (
                    <TableRow key={point.observacion_id ?? `${point.fecha}-${index}`}>
                      <TableCell align="center">{dayjs(point.fecha).format("DD/MM/YYYY")}</TableCell>
                      <TableCell align="center"><Chip size="small" color={origin.color} variant="outlined" label={origin.label} /></TableCell>
                      <TableCell align="center">{getPurchasedPresentationLabel(point)}</TableCell>
                      {showPrices ? <TableCell align="center">{point.precio_original === null ? "Sin dato" : formatCurrency(point.precio_original)}</TableCell> : null}
                      {showPrices ? <TableCell align="center">{formatCurrency(point.precio_promedio_normalizado)}</TableCell> : null}
                      <TableCell align="center" sx={{ color: variationTone(point.variacion_porcentual_anterior), fontWeight: 800 }}>
                        {point.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point.variacion_porcentual_anterior)}%`}
                      </TableCell>
                      <TableCell align="center">{point.fuentes.join(", ") || "-"}</TableCell>
                    </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
            ) : null}
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
}
