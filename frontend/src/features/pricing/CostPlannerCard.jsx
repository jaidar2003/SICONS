import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Alert, Box, Button, Card, CardContent, CircularProgress, FormControl, IconButton, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";

import { useCostPlanner } from "./useCostPlanner.js";
import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";

export function CostPlannerCard({ materiales, selectedMaterialId, forecastHorizon, token, showPrices }) {
  const {
    rows,
    plannerRows,
    summary,
    loading,
    error,
    addRow,
    removeRow,
    updateRow,
  } = useCostPlanner({ materiales, selectedMaterialId, forecastHorizon, token });

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
          <SectionHeader
            title="Planificador de costos multi-material"
            description="Suma el impacto de varios materiales sobre una parte de la obra."
            badge="HU19-HU20"
          />
          <Alert severity="info">Activá la vista de precios para proyectar costos totales de varios materiales.</Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Planificador de costos multi-material"
          description={`Proyecta el costo total de varios materiales usando el ultimo punto del horizonte actual de ${forecastHorizon} meses.`}
          badge="HU19-HU20"
          action={
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<AddIcon />}
              onClick={() => addRow("")}
            >
              Agregar material
            </Button>
          }
        />

        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          {loading ? (
            <Box className="flex justify-center py-4">
              <CircularProgress size={28} />
            </Box>
          ) : null}

          <Box className="grid gap-3">
            {rows.map((row, index) => (
              <Box key={row.id} className="grid gap-3 rounded-xl border border-slate-200 p-3 md:grid-cols-[minmax(240px,1.2fr)_180px_1fr_auto] md:items-end">
                <FormControl size="small">
                  <InputLabel id={`planner-material-${row.id}`}>Material</InputLabel>
                  <Select
                    labelId={`planner-material-${row.id}`}
                    label="Material"
                    value={row.materialId}
                    onChange={(event) => updateRow(row.id, "materialId", String(event.target.value))}
                  >
                    {materiales.map((material) => (
                      <MenuItem key={material.id} value={String(material.id)}>
                        {material.nombre} ({material.unidad_base})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <TextField
                  size="small"
                  label="Cantidad"
                  type="number"
                  value={row.quantity}
                  onChange={(event) => updateRow(row.id, "quantity", event.target.value)}
                  inputProps={{ min: 0, step: "any" }}
                />

                <Box className="rounded-lg bg-slate-50 px-3 py-2">
                  <Typography fontSize={12} fontWeight={800} color="text.secondary">
                    {plannerRows.find((item) => item.id === row.id)?.material?.unidad_base || "unidad"}
                  </Typography>
                  <Typography fontSize={13} color="text.secondary">
                    {plannerRows.find((item) => item.id === row.id)?.forecast
                      ? `Escenario ${plannerRows.find((item) => item.id === row.id)?.projectedPoint?.fecha || "-"}`
                      : "Esperando forecast"}
                  </Typography>
                </Box>

                <IconButton
                  color="secondary"
                  disabled={rows.length === 1}
                  onClick={() => removeRow(row.id)}
                  aria-label={`Eliminar fila ${index + 1}`}
                >
                  <DeleteOutlineIcon />
                </IconButton>
              </Box>
            ))}
          </Box>

          {summary ? (
            <>
              <Box className="grid gap-3 md:grid-cols-4">
                <SummaryMini label="Costo actual total" value={formatCurrency(summary.totalCurrent)} helper={`${summary.comparableRows.length} materiales con forecast`} />
                <SummaryMini label="Costo proyectado total" value={formatCurrency(summary.totalProjected)} helper={`Horizonte ${forecastHorizon} meses`} />
                <SummaryMini label="Impacto presupuestario" value={formatCurrency(summary.totalDelta)} helper={`${formatNumber(summary.totalDeltaPercent)}% sobre el costo actual`} />
                <SummaryMini label="Mayor impacto" value={summary.highestImpact.material.nombre} helper={formatCurrency(summary.highestImpact.delta)} />
              </Box>

              <Alert severity="info">
                Este resumen agrega el impacto presupuestario total de los materiales cargados y permite estimar una parte de la obra bajo un escenario comun de forecast.
              </Alert>

              <Box className="grid gap-2">
                {summary.comparableRows.map((row) => (
                  <Box key={row.id} className="grid gap-2 rounded-xl border border-slate-200 p-3 md:grid-cols-[1.1fr_.9fr_.9fr_.8fr] md:items-center">
                    <Box>
                      <Typography fontWeight={800}>{row.material.nombre}</Typography>
                      <Typography color="text.secondary" fontSize={13}>
                        {formatNumber(row.quantity, 0)} {row.material.unidad_base} - escenario {row.projectedPoint.fecha}
                      </Typography>
                    </Box>
                    <Typography fontWeight={700}>Actual: {formatCurrency(row.currentCost)}</Typography>
                    <Typography fontWeight={700}>Proyectado: {formatCurrency(row.projectedCost)}</Typography>
                    <Typography color={row.delta >= 0 ? "error.main" : "success.main"} fontWeight={800}>
                      {row.delta >= 0 ? "+" : "-"}
                      {formatCurrency(Math.abs(row.delta))}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </>
          ) : (
            <Alert severity="warning">Agregá materiales con cantidad valida para estimar el costo total proyectado.</Alert>
          )}
        </Stack>
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
