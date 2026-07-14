import { Accordion, AccordionDetails, AccordionSummary, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import ExpandMoreIconModule from "@mui/icons-material/ExpandMore";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { resolveMuiIcon } from "../../shared/components/resolveMuiIcon.js";
import { formatCurrency, formatNumber, variationTone } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

const ExpandMoreIcon = resolveMuiIcon(ExpandMoreIconModule);

export function HistoryTable({ serie, showPrices, selectedMaterial, className = "" }) {
  const presentation = getMaterialPresentation(selectedMaterial?.nombre, serie[0]?.unidad_base);
  const showBagEquivalents = presentation.type === "cement" && serie.some((point) => point.precio_equivalente_50kg !== null);

  return (
    <Card className={`h-full ${className}`}>
      <CardContent>
        <SectionHeader title="Historial de precios" description="Promedios mensuales por fecha, fuentes y variación contra el mes anterior." />
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight={800}>Ver tabla histórica</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell align="center">Fecha</TableCell>
                    {showPrices ? <TableCell align="center">{presentation.tablePriceLabel}</TableCell> : null}
                    {showPrices && showBagEquivalents ? <TableCell align="center">Bolsa 50 kg</TableCell> : null}
                    <TableCell align="center">Registros</TableCell>
                    <TableCell align="center">Variacion</TableCell>
                    <TableCell align="center">Fuentes</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {serie.map((point, index) => (
                    <TableRow key={point.observacion_id ?? `${point.fecha}-${index}`}>
                      <TableCell align="center">{point.fecha}</TableCell>
                      {showPrices ? <TableCell align="center">{formatCurrency(getDisplayPrice(point.precio_promedio_normalizado, selectedMaterial?.nombre, point.unidad_base))}</TableCell> : null}
                      {showPrices && showBagEquivalents ? <TableCell align="center">{formatCurrency(point.precio_equivalente_50kg)}</TableCell> : null}
                      <TableCell align="center">
                        {point.cantidad_registros} {point.cantidad_registros === 1 ? "precio" : "precios"}
                      </TableCell>
                      <TableCell align="center" sx={{ color: variationTone(point.variacion_porcentual_anterior), fontWeight: 800 }}>
                        {point.variacion_porcentual_anterior === null ? "-" : `${formatNumber(point.variacion_porcentual_anterior)}%`}
                      </TableCell>
                      <TableCell align="center">{point.fuentes.join(", ") || "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
}
