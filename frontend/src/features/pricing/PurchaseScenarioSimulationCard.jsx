import { Alert, Box, Button, ButtonGroup, Card, CardContent, CircularProgress, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { simulatePurchaseScenarios } from "./pricing.api.js";

const STRATEGY_LABELS = {
  COMPRAR_AHORA: "100% ahora",
  ESPERAR_AL_HORIZONTE: "100% futuro",
  COMPRA_PARCIAL: "Mixta",
};

const HORIZON_OPTIONS = [3, 6, 12];
const SHARE_OPTIONS = [
  { label: "0%", value: "0" },
  { label: "25%", value: "0.25" },
  { label: "50%", value: "0.50" },
  { label: "75%", value: "0.75" },
  { label: "100%", value: "1" },
];

export function PurchaseScenarioSimulationCard({ materiales, selectedMaterialId, token, showPrices }) {
  const [materialId, setMaterialId] = useState(selectedMaterialId || "");
  const [quantityInput, setQuantityInput] = useState("100");
  const [shareInput, setShareInput] = useState("0.50");
  const [horizons, setHorizons] = useState([3, 6, 12]);
  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (selectedMaterialId && !materialId) {
      setMaterialId(selectedMaterialId);
    }
  }, [materialId, selectedMaterialId]);

  const selectedMaterial = useMemo(
    () => materiales.find((material) => String(material.id) === String(materialId)),
    [materialId, materiales]
  );
  const quantity = Number(quantityInput);
  const share = Number(shareInput);
  const sharePercentage = Math.round(share * 100);
  const validQuantity = Number.isFinite(quantity) && quantity > 0;
  const validShare = Number.isFinite(share) && share >= 0 && share <= 1;

  function toggleHorizon(horizon) {
    setSimulation(null);
    setHorizons((current) => {
      if (current.includes(horizon)) {
        if (current.length <= 2) return current;
        return current.filter((item) => item !== horizon);
      }
      return [...current, horizon].sort((left, right) => left - right);
    });
  }

  async function handleSimulate() {
    setError("");
    setSimulation(null);

    if (!materialId) {
      setError("Seleccioná un material.");
      return;
    }

    if (!validQuantity) {
      setError("La cantidad debe ser mayor a cero.");
      return;
    }

    if (!validShare) {
      setError("La compra inmediata mixta debe estar entre 0 y 1.");
      return;
    }

    if (horizons.length < 2) {
      setError("Elegí al menos dos horizontes para comparar escenarios.");
      return;
    }

    setLoading(true);
    try {
      const result = await simulatePurchaseScenarios(
        {
          horizontes_meses: horizons,
          cantidad_objetivo: quantity,
          porcentaje_compra_inmediata: share,
        },
        token,
        materialId
      );
      setSimulation(result);
    } catch (simulationError) {
      setError(simulationError.message);
    } finally {
      setLoading(false);
    }
  }

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
          <SectionHeader
            title="Simulación temporal de compra"
            description="Consolida varios horizontes en una sola comparación de estrategias."
          />
          <Alert severity="info">Activá la vista de precios para simular escenarios temporales.</Alert>
        </CardContent>
      </Card>
    );
  }

  const bestScenario = simulation?.simulaciones?.reduce(
    (best, current) => (Number(current.ahorro_estimado) > Number(best.ahorro_estimado) ? current : best),
    simulation?.simulaciones?.[0]
  );

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Simulación temporal de compra"
          description="Compara 100% ahora, 100% futuro y compra mixta en varios horizontes dentro de una sola salida."
        />

        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Box className="grid gap-3 lg:grid-cols-[1.2fr_.7fr_.85fr] lg:items-start">
            <FormControl size="small">
              <InputLabel id="scenario-material">Material</InputLabel>
              <Select
                labelId="scenario-material"
                label="Material"
                value={materialId}
                onChange={(event) => {
                  setMaterialId(String(event.target.value));
                  setSimulation(null);
                }}
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
              label="Cantidad objetivo"
              type="number"
              value={quantityInput}
              onChange={(event) => {
                setQuantityInput(event.target.value);
                setSimulation(null);
              }}
              inputProps={{ min: 0, step: "any" }}
            />

            <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
              <Typography variant="body2" fontWeight={800} color="text.secondary" mb={1}>
                Compra inmediata mixta
              </Typography>
              <ButtonGroup size="small" variant="outlined" fullWidth>
                {SHARE_OPTIONS.map((option) => (
                  <Button
                    key={option.value}
                    variant={shareInput === option.value ? "contained" : "outlined"}
                    onClick={() => {
                      setShareInput(option.value);
                      setSimulation(null);
                    }}
                    sx={{ minWidth: 0 }}
                  >
                    {option.label}
                  </Button>
                ))}
              </ButtonGroup>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Compra {sharePercentage}% ahora y deja {100 - sharePercentage}% para despues.
              </Typography>
            </Box>
          </Box>

          <Box className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <Box>
              <Typography variant="body2" fontWeight={800} color="text.secondary">
                Horizontes a comparar
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Mantené al menos dos para ver escenarios comparables.
              </Typography>
            </Box>
            <ButtonGroup size="small" variant="outlined">
              {HORIZON_OPTIONS.map((horizon) => (
                <Button
                  key={horizon}
                  variant={horizons.includes(horizon) ? "contained" : "outlined"}
                  onClick={() => toggleHorizon(horizon)}
                >
                  {horizon} meses
                </Button>
              ))}
            </ButtonGroup>
            <Button variant="contained" onClick={handleSimulate} disabled={loading}>
              {loading ? "Simulando..." : "Simular escenarios"}
            </Button>
          </Box>

          {loading ? (
            <Box className="flex justify-center py-2">
              <CircularProgress size={24} />
            </Box>
          ) : null}

          {simulation ? (
            <Box className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              <Box className="grid gap-3 md:grid-cols-4">
                <SummaryMini
                  label="Material"
                  value={selectedMaterial?.nombre || simulation.material_key}
                  helper={selectedMaterial?.unidad_base || "Unidad base"}
                />
                <SummaryMini
                  label="Cantidad"
                  value={formatNumber(simulation.cantidad_objetivo, 0)}
                  helper={`${formatNumber(Number(simulation.porcentaje_compra_inmediata) * 100, 0)}% inmediato en mixta`}
                />
                <SummaryMini
                  label="Mejor horizonte"
                  value={bestScenario ? `${bestScenario.horizonte_meses} meses` : "-"}
                  helper={bestScenario ? STRATEGY_LABELS[bestScenario.mejor_estrategia] || bestScenario.mejor_estrategia : "-"}
                />
                <SummaryMini
                  label="Mayor ahorro"
                  value={bestScenario ? formatCurrency(bestScenario.ahorro_estimado) : "-"}
                  helper="Contra la alternativa mas costosa"
                />
              </Box>

              <Box className="grid gap-3">
                {simulation.simulaciones.map((scenario) => (
                  <Box key={scenario.horizonte_meses} className="rounded-xl border border-slate-200 p-3">
                    <Box className="mb-2 grid gap-2 md:grid-cols-[1fr_auto] md:items-start">
                      <Box>
                        <Typography variant="h3">Horizonte {scenario.horizonte_meses} meses</Typography>
                        <Typography variant="body2" color="text.secondary">
                          Mejor estrategia: {STRATEGY_LABELS[scenario.mejor_estrategia] || scenario.mejor_estrategia} · Confiabilidad {scenario.confiabilidad}
                        </Typography>
                      </Box>
                      <Typography fontWeight={900} color="success.main">
                        Ahorro {formatCurrency(scenario.ahorro_estimado)}
                      </Typography>
                    </Box>

                    <Box className="grid gap-2">
                      {scenario.estrategias.map((strategy) => (
                        <Box
                          key={`${scenario.horizonte_meses}-${strategy.nombre}`}
                          className="grid gap-2 rounded-lg bg-slate-50 px-3 py-2 md:grid-cols-[1fr_.7fr_.7fr] md:items-center"
                        >
                          <Box>
                            <Typography fontWeight={800}>
                              {STRATEGY_LABELS[strategy.nombre] || strategy.nombre}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {strategy.descripcion}
                            </Typography>
                          </Box>
                          <Typography fontWeight={800}>Costo {formatCurrency(strategy.costo_estimado)}</Typography>
                          <Typography color="text.secondary" fontWeight={800}>
                            Riesgo {strategy.riesgo}
                          </Typography>
                        </Box>
                      ))}
                    </Box>

                    {scenario.advertencias?.length ? (
                      <Alert className="mt-2" severity="warning">
                        {scenario.advertencias.join(" ")}
                      </Alert>
                    ) : null}
                  </Box>
                ))}
              </Box>
            </Box>
          ) : (
            <Alert severity="info">
              Esta simulación consolida múltiples horizontes temporales y deja la comparación lista para decidir sin cambiar de vista.
            </Alert>
          )}
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
