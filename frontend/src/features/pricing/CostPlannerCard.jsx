import AddIcon from "@mui/icons-material/Add";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { Alert, Box, Button, ButtonGroup, Card, CardContent, CircularProgress, FormControl, IconButton, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { useCostPlanner } from "./useCostPlanner.js";
import { optimizePurchaseBudget, prioritizeMaterials } from "./pricing.api.js";
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
    storedBudgetInput,
    setBudgetPersisted,
  } = useCostPlanner({ materiales, selectedMaterialId, forecastHorizon, token });
  const [budgetInput, setBudgetInput] = useState("");
  const [budgetTouched, setBudgetTouched] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizationError, setOptimizationError] = useState("");
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [prioritizing, setPrioritizing] = useState(false);
  const [prioritizationError, setPrioritizationError] = useState("");
  const [prioritizationResult, setPrioritizationResult] = useState(null);
  const [openSection, setOpenSection] = useState("budget");

  const optimizationItems = useMemo(
    () =>
      plannerRows
        .filter((row) => row.material && row.validQuantity)
        .map((row) => ({
          material_id: Number(row.material.id),
          cantidad_objetivo: row.quantity,
          criticidad: row.criticidad || "media",
        })),
    [plannerRows]
  );

  const prioritizationItems = useMemo(
    () =>
      plannerRows
        .filter((row) => row.material && row.validQuantity)
        .map((row) => ({
          material_id: Number(row.material.id),
          cantidad_requerida: row.quantity,
        })),
    [plannerRows]
  );

  useEffect(() => {
    if (storedBudgetInput && !budgetTouched) {
      setBudgetInput(storedBudgetInput);
      return;
    }

    if (budgetTouched || !summary) return;
    const suggestedBudget = Number(summary.totalCurrent || 0);
    if (suggestedBudget > 0) {
      setBudgetInput(suggestedBudget.toFixed(2));
      setBudgetPersisted(suggestedBudget.toFixed(2));
    }
  }, [budgetTouched, setBudgetPersisted, storedBudgetInput, summary]);

  async function handleOptimizeBudget() {
    setOptimizationError("");
    setOptimizationResult(null);

    const presupuestoTotal = Number(budgetInput);
    if (!Number.isFinite(presupuestoTotal) || presupuestoTotal <= 0) {
      setOptimizationError("Ingresá un presupuesto mayor a cero para optimizar.");
      return;
    }

    if (!optimizationItems.length) {
      setOptimizationError("Agregá al menos un material válido para optimizar.");
      return;
    }

    setOptimizing(true);
    try {
      const result = await optimizePurchaseBudget(
        {
          presupuesto_total: presupuestoTotal,
          horizonte_meses: forecastHorizon,
          materiales: optimizationItems,
        },
        token
      );
      setOptimizationResult(result);
    } catch (optimizeError) {
      setOptimizationError(optimizeError.message);
    } finally {
      setOptimizing(false);
    }
  }

  async function handlePrioritizeMaterials() {
    setPrioritizationError("");
    setPrioritizationResult(null);

    if (!prioritizationItems.length) {
      setPrioritizationError("Agregá al menos un material válido para priorizar.");
      return;
    }

    setPrioritizing(true);
    try {
      const result = await prioritizeMaterials(
        {
          horizonte_meses: forecastHorizon,
          materiales: prioritizationItems,
        },
        token
      );
      setPrioritizationResult(result);
    } catch (prioritizeError) {
      setPrioritizationError(prioritizeError.message);
    } finally {
      setPrioritizing(false);
    }
  }

  const optimizationHeadline = useMemo(() => {
    if (!optimizationResult) return "";

    const restante = Number(optimizationResult.presupuesto_restante || 0);
    const total = Number(optimizationResult.presupuesto_total || 0);
    const usado = Number(optimizationResult.presupuesto_utilizado || 0);

    if (restante <= 0) {
      return "La optimizacion uso todo el presupuesto disponible y priorizo los materiales mas convenientes segun criticidad y ahorro esperado.";
    }

    if (usado <= 0) {
      return "No se pudo asignar presupuesto util con los materiales cargados. Revisá cantidades, criticidad y forecast.";
    }

    return `La optimizacion asigno ${formatCurrency(usado)} de ${formatCurrency(total)} y dejo ${formatCurrency(restante)} sin usar para preservar margen.`;
  }, [optimizationResult]);

  const planningDecision = useMemo(() => {
    if (!summary) return null;

    const action = summary.totalDelta > 0 ? "Comprar ahora" : "Esperar";
    const detail =
      summary.totalDelta > 0
        ? `El total proyectado sube ${formatCurrency(summary.totalDelta)} frente al costo actual.`
        : `El total proyectado baja ${formatCurrency(Math.abs(summary.totalDelta))} frente al costo actual.`;

    return {
      action,
      detail,
      highestImpactName: summary.highestImpact.material?.nombre || "-",
      highestImpactValue: summary.highestImpact.delta,
    };
  }, [summary]);

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
        <SectionHeader
          title="Planificador de costos multi-material"
          description="Suma el impacto de varios materiales sobre una parte de la obra."
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
          <ButtonGroup size="small" variant="outlined">
            <Button variant={openSection === "budget" ? "contained" : "outlined"} onClick={() => setOpenSection("budget")}>
              Resumen
            </Button>
            <Button variant={openSection === "optimize" ? "contained" : "outlined"} onClick={() => setOpenSection("optimize")}>
              Optimización
            </Button>
            <Button variant={openSection === "priority" ? "contained" : "outlined"} onClick={() => setOpenSection("priority")}>
              Criticidad
            </Button>
          </ButtonGroup>

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
                  <Typography variant="body2" fontWeight={800} color="text.secondary">
                    {plannerRows.find((item) => item.id === row.id)?.material?.unidad_base || "unidad"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
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

          {openSection === "budget" || openSection === "optimize" ? (
          <Box className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <Stack spacing={2}>
              <Box className="grid gap-3 md:grid-cols-[220px_1fr_auto] md:items-end">
                <TextField
                  label="Presupuesto disponible"
                  type="number"
                  value={budgetInput}
                  onChange={(event) => {
                    setBudgetTouched(true);
                    setBudgetInput(event.target.value);
                    setBudgetPersisted(event.target.value);
                  }}
                  inputProps={{ min: 0, step: "any" }}
                  helperText="La optimización usa el horizonte activo y prioriza criticidad + ahorro esperado."
                />
                <Box className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <Typography variant="body2" fontWeight={800} color="text.secondary">
                    Sugerencia rápida
                  </Typography>
                  <Typography variant="subtitle1">
                    {summary ? `Presupuesto sugerido ${formatCurrency(summary.totalCurrent)}` : "Completá materiales válidos"}
                  </Typography>
                </Box>
                <Button variant="contained" color="primary" onClick={handleOptimizeBudget} disabled={optimizing}>
                  {optimizing ? "Optimizando..." : "Optimizar presupuesto"}
                </Button>
              </Box>

              {openSection === "optimize" ? (
                <>
                  {optimizationError ? <Alert severity="error">{optimizationError}</Alert> : null}
                  {!optimizationResult && !optimizationError ? (
                    <Alert severity="info">
                      La optimización real usa PuLP en el backend. Devuelve cuánto conviene comprar ahora dentro del presupuesto,
                      respetando criticidad y el forecast activo.
                    </Alert>
                  ) : null}

                  {optimizationResult ? (
                    <Button
                      variant="outlined"
                      color="secondary"
                      startIcon={<ContentCopyIcon />}
                      onClick={async () => {
                        const lineas = [
                          "Resumen operativo de costos",
                          `Presupuesto total: ${formatCurrency(optimizationResult.presupuesto_total)}`,
                          `Presupuesto utilizado: ${formatCurrency(optimizationResult.presupuesto_utilizado)}`,
                          `Presupuesto restante: ${formatCurrency(optimizationResult.presupuesto_restante)}`,
                          `Ahorro estimado: ${formatCurrency(optimizationResult.ahorro_total_estimado)}`,
                          `Decision: ${optimizationHeadline}`,
                        ];
                        await navigator.clipboard.writeText(lineas.join("\n"));
                      }}
                    >
                      Copiar resumen operativo
                    </Button>
                  ) : null}
                </>
              ) : (
                <>
                  {optimizationError ? <Alert severity="error">{optimizationError}</Alert> : null}
                  {!optimizationResult && !optimizationError ? (
                    <Alert severity="info">
                      La optimización real usa PuLP en el backend. Devuelve cuánto conviene comprar ahora dentro del presupuesto,
                      respetando criticidad y el forecast activo.
                    </Alert>
                  ) : null}
                </>
              )}
            </Stack>
          </Box>
          ) : null}

          {openSection === "priority" ? (
          <Box className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <Stack spacing={2}>
              <Box className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                <Box>
                  <Typography variant="subtitle1">
                    Priorizar materiales cargados
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    Ordena los materiales del planificador segun criticidad e impacto presupuestario.
                  </Typography>
                </Box>
                <Button variant="outlined" color="secondary" onClick={handlePrioritizeMaterials} disabled={prioritizing}>
                  {prioritizing ? "Priorizando..." : "Calcular criticidad"}
                </Button>
              </Box>

              {prioritizationError ? <Alert severity="error">{prioritizationError}</Alert> : null}
              {!prioritizationResult && !prioritizationError ? (
                <Alert severity="info">
                  El ranking usa el forecast activo y devuelve una lectura operativa para decidir qué material conviene anticipar.
                </Alert>
              ) : null}

              {prioritizationResult ? (
                <Box className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4">
                  <Box className="grid gap-3 md:grid-cols-4">
                    <SummaryMini
                      label="Horizonte"
                      value={`${prioritizationResult.horizonte_meses} meses`}
                      helper={`alpha ${formatNumber(Number(prioritizationResult.alpha))} / beta ${formatNumber(Number(prioritizationResult.beta))}`}
                    />
                    <SummaryMini
                      label="Materiales"
                      value={prioritizationResult.materiales.length}
                      helper="Cargados en el ranking"
                    />
                    <SummaryMini
                      label="Top prioridad"
                      value={prioritizationResult.materiales[0]?.material_nombre || "-"}
                      helper={prioritizationResult.materiales[0]?.nivel_criticidad || "-"}
                    />
                    <SummaryMini
                      label="Mayor impacto"
                      value={formatCurrency(
                        prioritizationResult.materiales.reduce(
                          (max, row) => (Number(row.impacto_absoluto) > max ? Number(row.impacto_absoluto) : max),
                          0
                        )
                      )}
                      helper="Entre los materiales cargados"
                    />
                  </Box>

                  <Box className="grid gap-2">
                    {prioritizationResult.materiales.map((item, index) => (
                      <Box
                        key={item.material_id}
                        className="grid gap-2 rounded-xl border border-slate-200 p-3 md:grid-cols-[1.2fr_.8fr_.8fr_.8fr] md:items-center"
                      >
                        <Box>
                          <Typography variant="h3">
                            {index + 1}. {item.material_nombre}
                          </Typography>
                          <Typography color="text.secondary" variant="body2">
                            {item.explicacion}
                          </Typography>
                        </Box>
                        <Typography fontWeight={700}>Nivel: {item.nivel_criticidad}</Typography>
                        <Typography fontWeight={700}>Impacto: {formatCurrency(Number(item.impacto_absoluto))}</Typography>
                        <Typography color="success.main" fontWeight={800}>
                          Variacion: {formatNumber(Number(item.variacion_esperada_porcentual))}%
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              ) : null}
            </Stack>
          </Box>
          ) : null}

          {openSection === "budget" && summary ? (
            <>
              {planningDecision ? (
                <Box className="rounded-2xl border border-slate-200 bg-white p-4">
                  <Box className="grid gap-3 md:grid-cols-[1.25fr_.75fr_.75fr] md:items-center">
                    <Box>
                      <Typography variant="overline" color="text.secondary">
                        Decision principal
                      </Typography>
                      <Typography variant="h2" lineHeight={1.15}>
                        {planningDecision.action}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" mt={0.5}>
                        {planningDecision.detail}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" fontWeight={800} color="text.secondary">
                        Mayor impacto
                      </Typography>
                      <Typography variant="h3">
                        {planningDecision.highestImpactName}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" fontWeight={800} color="text.secondary">
                        Impacto esperado
                      </Typography>
                      <Typography variant="h3" fontWeight={900} color={planningDecision.highestImpactValue >= 0 ? "error.main" : "success.main"}>
                        {planningDecision.highestImpactValue >= 0 ? "+" : "-"}
                        {formatCurrency(Math.abs(planningDecision.highestImpactValue))}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              ) : null}

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
                      <Typography variant="h3">{row.material.nombre}</Typography>
                      <Typography color="text.secondary" variant="body2">
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
          ) : openSection === "budget" ? (
            <Alert severity="warning">Agregá materiales con cantidad valida para estimar el costo total proyectado.</Alert>
          ) : null}

          {openSection === "optimize" && optimizationResult ? (
            <Box className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              <Box className="grid gap-3 md:grid-cols-4">
                <SummaryMini
                  label="Presupuesto total"
                  value={formatCurrency(optimizationResult.presupuesto_total)}
                  helper={`Horizonte ${optimizationResult.horizonte_meses} meses`}
                />
                <SummaryMini
                  label="Presupuesto utilizado"
                  value={formatCurrency(optimizationResult.presupuesto_utilizado)}
                  helper={`${optimizationResult.estado_optimizacion} / optimizado`}
                />
                <SummaryMini
                  label="Presupuesto restante"
                  value={formatCurrency(optimizationResult.presupuesto_restante)}
                  helper="Saldo no asignado"
                />
                <SummaryMini
                  label="Ahorro estimado"
                  value={formatCurrency(optimizationResult.ahorro_total_estimado)}
                  helper="Suma ponderada por criticidad"
                />
              </Box>

              <Alert severity="success">
                <Typography variant="subtitle1" mb={0.5}>
                  Resultado operativo
                </Typography>
                <Typography variant="body2">{optimizationHeadline}</Typography>
                <Typography variant="body2" mt={0.75}>
                  {optimizationResult.justificacion}
                </Typography>
              </Alert>

              {optimizationResult.advertencias?.length ? (
                <Alert severity="warning">
                  <Box className="grid gap-1">
                    {optimizationResult.advertencias.map((warning, index) => (
                      <Typography key={`${warning}-${index}`} variant="body2">
                        {warning}
                      </Typography>
                    ))}
                  </Box>
                </Alert>
              ) : null}

              <Box className="grid gap-2">
                {optimizationResult.items.map((item) => (
                  <Box key={item.material_id} className="grid gap-2 rounded-xl border border-slate-200 p-3 md:grid-cols-[1.3fr_.8fr_.8fr_.8fr] md:items-center">
                    <Box>
                      <Typography variant="h3">{item.material_key}</Typography>
                      <Typography color="text.secondary" variant="body2">
                        Criticidad {item.criticidad} · Confiabilidad {item.confiabilidad}
                      </Typography>
                    </Box>
                    <Typography fontWeight={700}>
                      Comprar ahora: {formatNumber(item.cantidad_recomendada_comprar_ahora, 4)}
                    </Typography>
                    <Typography fontWeight={700}>Costo hoy: {formatCurrency(item.costo_compra_ahora)}</Typography>
                    <Typography color="success.main" fontWeight={800}>
                      Ahorro: {formatCurrency(item.ahorro_total_estimado)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

function SummaryMini({ label, value, helper }) {
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
