import { Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber, monthLabel, variationTone } from "../../shared/utils/formatters.js";

export function HistoryTable({ serie, showPrices }) {
  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader title="Historial de precios" description="Promedio mensual, cantidad de precios usados, fuentes y variacion contra el mes anterior." />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell align="center">Mes</TableCell>
                {showPrices ? <TableCell align="center">Precio/kg</TableCell> : null}
                {showPrices ? <TableCell align="center">25 kg</TableCell> : null}
                {showPrices ? <TableCell align="center">50 kg</TableCell> : null}
                <TableCell align="center">Muestra</TableCell>
                <TableCell align="center">Variacion</TableCell>
                <TableCell align="center">Fuentes</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {serie.map((point) => (
                <TableRow key={point.fecha}>
                  <TableCell align="center">{monthLabel(point.fecha)}</TableCell>
                  {showPrices ? <TableCell align="center">{formatCurrency(point.precio_promedio_normalizado)}</TableCell> : null}
                  {showPrices ? <TableCell align="center">{formatCurrency(point.precio_equivalente_25kg)}</TableCell> : null}
                  {showPrices ? <TableCell align="center">{formatCurrency(point.precio_equivalente_50kg)}</TableCell> : null}
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
      </CardContent>
    </Card>
  );
}
