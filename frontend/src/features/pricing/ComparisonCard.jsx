import { Box, Card, CardContent, Divider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatPercentChange, monthLabel, variationTone } from "../../shared/utils/formatters.js";
import { getDisplayPrice, getMaterialPresentation } from "./materialPresentation.js";

export function ComparisonCard({ rows, selectedMaterialId, showPrices, compact = false, className = "" }) {
  const selectedRow = rows.find((row) => String(row.material.id) === String(selectedMaterialId));
  const highestRow = rows[rows.length - 1];
  const summary = !rows.length
    ? "No hay datos para comparar en el periodo seleccionado."
    : selectedRow
      ? showPrices
        ? `${selectedRow.material.nombre}: ${formatCurrency(getDisplayPrice(selectedRow.firstValue, selectedRow.material.nombre, selectedRow.last.unidad_base))} a ${formatCurrency(getDisplayPrice(selectedRow.lastValue, selectedRow.material.nombre, selectedRow.last.unidad_base))} ${getMaterialPresentation(selectedRow.material.nombre, selectedRow.last.unidad_base).summaryUnitText}, cambio ${formatPercentChange(selectedRow.variation)} entre ${monthLabel(selectedRow.first.fecha)} y ${monthLabel(selectedRow.last.fecha)}. Mayor suba: ${highestRow.material.nombre} (${formatPercentChange(highestRow.variation)}).`
        : `${selectedRow.material.nombre}: cambio ${formatPercentChange(selectedRow.variation)} entre ${monthLabel(selectedRow.first.fecha)} y ${monthLabel(selectedRow.last.fecha)}. Mayor suba: ${highestRow.material.nombre} (${formatPercentChange(highestRow.variation)}).`
      : `Mayor suba: ${highestRow.material.nombre} (${formatPercentChange(highestRow.variation)}).`;

  return (
    <Card className={`h-full ${className}`}>
      <CardContent>
        <SectionHeader
          title={compact ? "Comparacion rapida" : "Comparacion entre materiales"}
          description={compact ? "Orden simple por variacion del periodo." : "Precio inicial, precio final y cambio total del periodo."}
          badge={compact ? null : "Resumen"}
        />
        {!compact ? (
          <Typography className="rounded-md border border-blue-100 bg-md-container px-3 py-2" color="text.secondary" fontWeight={600} mb={1.5}>
            {summary}
          </Typography>
        ) : null}
        {compact ? (
          <Box className="flex flex-col overflow-hidden rounded-md border border-slate-200 bg-white">
            {rows.map((row, index) => {
              const isSelected = String(row.material.id) === String(selectedMaterialId);
              const presentation = getMaterialPresentation(row.material.nombre, row.last.unidad_base);
              return (
                <Box key={row.material.id} className={isSelected ? "bg-md-container" : "bg-white"}>
                  <Box className="grid gap-3 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                    <Box className="min-w-0">
                      <Typography fontWeight={900} lineHeight={1.2}>
                        {row.material.nombre}
                      </Typography>
                      <Typography color="text.secondary" fontSize={12} mt={0.25}>
                        {monthLabel(row.first.fecha)} a {monthLabel(row.last.fecha)} - {presentation.displayUnitLabel}
                      </Typography>
                    </Box>
                    <Box className="flex items-center justify-between gap-3 sm:justify-end">
                      <Box className="text-right">
                        <Typography fontSize={18} fontWeight={950} lineHeight={1.1} sx={{ color: variationTone(row.variation) }}>
                          {formatPercentChange(row.variation)}
                        </Typography>
                        <Typography color="text.secondary" fontSize={12}>
                          {showPrices
                            ? `${formatCurrency(getDisplayPrice(row.lastValue, row.material.nombre, row.last.unidad_base))} final`
                            : `${row.sampleSize} registros`}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  {index < rows.length - 1 ? <Divider /> : null}
                </Box>
              );
            })}
          </Box>
        ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Material</TableCell>
                {showPrices ? <TableCell align="right">Inicio</TableCell> : null}
                {showPrices ? <TableCell align="right">Final</TableCell> : null}
                {showPrices ? <TableCell align="right">Cambio $</TableCell> : null}
                <TableCell align="center">Cambio %</TableCell>
                <TableCell align="center">Muestra</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => {
                const isSelected = String(row.material.id) === String(selectedMaterialId);
                const presentation = getMaterialPresentation(row.material.nombre, row.last.unidad_base);
                return (
                  <TableRow key={row.material.id} selected={isSelected}>
                    <TableCell>
                      <Typography fontWeight={800}>{row.material.nombre}</Typography>
                      <Typography color="text.secondary" fontSize={12}>
                        {monthLabel(row.first.fecha)} a {monthLabel(row.last.fecha)} - {presentation.displayUnitLabel}
                      </Typography>
                    </TableCell>
                    {showPrices ? <TableCell align="right">{formatCurrency(getDisplayPrice(row.firstValue, row.material.nombre, row.last.unidad_base))}</TableCell> : null}
                    {showPrices ? <TableCell align="right">{formatCurrency(getDisplayPrice(row.lastValue, row.material.nombre, row.last.unidad_base))}</TableCell> : null}
                    {showPrices ? (
                      <TableCell align="right" sx={{ color: variationTone(row.variation), fontWeight: 800 }}>
                        {formatCurrency(getDisplayPrice(row.lastValue - row.firstValue, row.material.nombre, row.last.unidad_base))}
                      </TableCell>
                    ) : null}
                    <TableCell align="center" sx={{ color: variationTone(row.variation), fontWeight: 800 }}>
                      {formatPercentChange(row.variation)}
                    </TableCell>
                    <TableCell align="center">{row.sampleSize} registros</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}
