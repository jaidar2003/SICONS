import { Alert, Box, Button, ButtonGroup, Card, CardContent, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { comparePurchaseStrategies, recommendContextualPurchase } from "./pricing.api.js";

const DECISION_LABELS = {
  COMPRAR_AHORA: "Comprar ahora",
  ESPERAR: "Esperar",
  MONITOREAR: "Monitorear",
  POSTERGAR: "Postergar",
  ESCALONAR: "Escalonar",
  SIN_VENTAJA_CLARA: "Sin ventaja clara",
  COMPRAR_AHORA_AL_HORIZONTE: "Comprar ahora al horizonte",
  ESPERAR_AL_HORIZONTE: "Esperar al horizonte",
};

const STRATEGY_LABELS = {
  COMPRAR_AHORA: "Comprar ahora",
  ESPERAR_AL_HORIZONTE: "Esperar al horizonte",
  COMPRA_PARCIAL: "Compra parcial",
};

const SHARE_OPTIONS = [
  { label: "0%", value: "0" },
  { label: "25%", value: "0.25" },
  { label: "50%", value: "0.50" },
  { label: "75%", value: "0.75" },
  { label: "100%", value: "1" },
];
const HORIZON_OPTIONS = Array.from({ length: 12 }, (_, index) => index + 1);
const PHASE_OPTIONS = [
  { value: "estructura", label: "Estructura" },
  { value: "terminaciones", label: "Terminaciones" },
  { value: "impermeabilizacion", label: "Impermeabilización" },
  { value: "general", label: "General" },
];
const RISK_OPTIONS = [
  { value: "baja", label: "Baja" },
  { value: "media", label: "Media" },
  { value: "alta", label: "Alta" },
];

export function PurchaseDecisionCard({ materiales, selectedMaterialId, forecastHorizon, token, showPrices }) {
  const [materialId, setMaterialId] = useState(selectedMaterialId || "");
  const [decisionHorizon, setDecisionHorizon] = useState(forecastHorizon);
  const [quantityInput, setQuantityInput] = useState("100");
  const [faseObra, setFaseObra] = useState("general");
  const [targetDate, setTargetDate] = useState("");
  const [toleranciaRiesgo, setToleranciaRiesgo] = useState("media");
  const [recommendation, setRecommendation] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loadingRecommendation, setLoadingRecommendation] = useState(false);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [error, setError] = useState("");
  const [comparisonShare, setComparisonShare] = useState("0.50");

  useEffect(() => {
    if (selectedMaterialId && !materialId) {
      setMaterialId(selectedMaterialId);
    }
  }, [materialId, selectedMaterialId]);

  useEffect(() => {
    setRecommendation(null);
    setComparison(null);
  }, [decisionHorizon, faseObra, materialId, quantityInput, targetDate, toleranciaRiesgo]);

  const selectedMaterial = useMemo(
    () => materiales.find((material) => String(material.id) === String(materialId)),
    [materialId, materiales]
  );

  const quantity = Number(quantityInput);
  const sharePercentage = Math.round(Number(comparisonShare) * 100);
  const validQuantity = Number.isFinite(quantity) && quantity > 0;
  const validShare = Number.isFinite(Number(comparisonShare)) && Number(comparisonShare) >= 0 && Number(comparisonShare) <= 1;

  async function handleRecommend() {
    setError("");
    setRecommendation(null);

    if (!materialId) {
      setError("Seleccioná un material.");
      return;
    }
    if (!validQuantity) {
      setError("La cantidad debe ser mayor a cero.");
      return;
    }

    setLoadingRecommendation(true);
    try {
      const result = await recommendContextualPurchase(
        {
          cantidad_objetivo: quantity,
          fase_obra: faseObra,
          tolerancia_riesgo: toleranciaRiesgo,
          ...(targetDate ? { fecha_objetivo_uso: targetDate } : { horizonte_meses: decisionHorizon }),
        },
        token,
        materialId
      );
      setRecommendation(result);
    } catch (recommendError) {
      setError(recommendError.message);
    } finally {
      setLoadingRecommendation(false);
    }
  }

  async function handleCompare() {
    setError("");
    setComparison(null);

    if (!materialId) {
      setError("Seleccioná un material.");
      return;
    }
    if (!validQuantity) {
      setError("La cantidad debe ser mayor a cero.");
      return;
    }
    if (!validShare) {
      setError("La porción a comprar ahora debe estar entre 0 y 1.");
      return;
    }

    setLoadingComparison(true);
    try {
      const result = await comparePurchaseStrategies(
        {
          horizonte_meses: decisionHorizon,
          cantidad_objetivo: quantity,
          porcentaje_compra_inmediata: Number(comparisonShare),
        },
        token,
        materialId
      );
      setComparison(result);
    } catch (compareError) {
      setError(compareError.message);
    } finally {
      setLoadingComparison(false);
    }
  }

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
          <SectionHeader
            title="Decisiones por material"
            description="Recomendación contextual por etapa de obra y comparación de estrategias de compra."
        />
          <Alert severity="info">Activá la vista de precios para calcular recomendaciones y comparar estrategias.</Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Decisiones por material"
          description="Evalúa fase de obra, fecha objetivo y tolerancia al riesgo para recomendar cuándo comprar un material puntual."
        />

        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Box className="grid gap-3 lg:grid-cols-3 lg:items-end">
            <FormControl size="small">
              <InputLabel id="decision-material">Material</InputLabel>
              <Select
                labelId="decision-material"
                label="Material"
                value={materialId}
                onChange={(event) => setMaterialId(String(event.target.value))}
              >
                {materiales.map((material) => (
                  <MenuItem key={material.id} value={String(material.id)}>
                    {material.nombre} ({material.unidad_base})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small">
              <InputLabel id="decision-phase">Fase de obra</InputLabel>
              <Select
                labelId="decision-phase"
                label="Fase de obra"
                value={faseObra}
                onChange={(event) => setFaseObra(String(event.target.value))}
              >
                {PHASE_OPTIONS.map((phase) => (
                  <MenuItem key={phase.value} value={phase.value}>
                    {phase.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              size="small"
              label="Cantidad objetivo"
              type="number"
              value={quantityInput}
              onChange={(event) => setQuantityInput(event.target.value)}
              inputProps={{ min: 0, step: "any" }}
            />

          </Box>

          <Box className="grid gap-3 lg:grid-cols-4 lg:items-end">
            <FormControl size="small">
              <InputLabel id="decision-horizon">Horizonte sin fecha</InputLabel>
              <Select
                labelId="decision-horizon"
                label="Horizonte sin fecha"
                value={decisionHorizon}
                onChange={(event) => setDecisionHorizon(Number(event.target.value))}
                disabled={Boolean(targetDate)}
              >
                {HORIZON_OPTIONS.map((horizon) => (
                  <MenuItem key={horizon} value={horizon}>
                    {horizon} {horizon === 1 ? "mes" : "meses"}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              size="small"
              label="Fecha objetivo (opcional)"
              type="date"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value)}
              InputLabelProps={{ shrink: true }}
            />

            <FormControl size="small">
              <InputLabel id="decision-risk">Tolerancia al riesgo</InputLabel>
              <Select
                labelId="decision-risk"
                label="Tolerancia al riesgo"
                value={toleranciaRiesgo}
                onChange={(event) => setToleranciaRiesgo(String(event.target.value))}
              >
                {RISK_OPTIONS.map((risk) => (
                  <MenuItem key={risk.value} value={risk.value}>
                    {risk.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Typography variant="body2" color="text.secondary">
              Si informás fecha objetivo, el sistema calcula el horizonte de evaluación automáticamente.
            </Typography>
          </Box>

          <Box className="grid gap-3 lg:grid-cols-[minmax(320px,1fr)_minmax(0,1.4fr)] lg:items-end">
            <Box className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
              <Typography variant="body2" fontWeight={800} color="text.secondary" mb={1}>
                Compra inmediata
              </Typography>
              <ButtonGroup size="small" variant="outlined" fullWidth>
                {SHARE_OPTIONS.map((option) => (
                  <Button
                    key={option.value}
                    variant={comparisonShare === option.value ? "contained" : "outlined"}
                    onClick={() => setComparisonShare(option.value)}
                    sx={{ minWidth: 0 }}
                  >
                    {option.label}
                  </Button>
                ))}
              </ButtonGroup>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Compra {sharePercentage}% ahora y deja {100 - sharePercentage}% para el horizonte.
              </Typography>
            </Box>
            <Box className="grid gap-3 sm:grid-cols-2">
              <Button variant="contained" color="primary" onClick={handleRecommend} disabled={loadingRecommendation} sx={{ minHeight: 44 }}>
                {loadingRecommendation ? "Calculando..." : "Calcular recomendacion"}
              </Button>
              <Button variant="outlined" color="secondary" onClick={handleCompare} disabled={loadingComparison} sx={{ minHeight: 44 }}>
                {loadingComparison ? "Comparando..." : "Comparar estrategias"}
              </Button>
            </Box>
          </Box>

          {recommendation ? (
            <Box className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              <Box className="grid gap-3 md:grid-cols-4">
                <SummaryMini
                  label="Decision"
                  value={DECISION_LABELS[recommendation.decision] || recommendation.decision}
                  helper={`Horizonte ${recommendation.horizonte_meses} meses`}
                />
                <SummaryMini
                  label="Variacion esperada"
                  value={recommendation.variacion_esperada_pct === null ? "-" : `${formatNumber(recommendation.variacion_esperada_pct)}%`}
                  helper={`Fase ${recommendation.fase_obra} / criticidad ${recommendation.criticidad}`}
                />
                <SummaryMini label="Confiabilidad" value={recommendation.confiabilidad} helper={`Riesgo ${recommendation.tolerancia_riesgo}`} />
                <SummaryMini label="Material" value={selectedMaterial?.nombre || "-"} helper={selectedMaterial?.unidad_base || "-"} />
              </Box>

              <Alert severity="success">
                <Typography fontWeight={800} mb={0.5}>
                  Recomendacion
                </Typography>
                <Typography fontSize={14}>
                  {recommendation.justificacion}
                </Typography>
              </Alert>

              {recommendation.advertencias?.length ? (
                <Alert severity="warning">
                  <Box className="grid gap-1">
                    {recommendation.advertencias.map((warning, index) => (
                      <Typography key={`${warning}-${index}`} fontSize={13}>
                        {warning}
                      </Typography>
                    ))}
                  </Box>
                </Alert>
              ) : null}
            </Box>
          ) : null}

          {comparison ? (
            <Box className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              <Box className="grid gap-3 md:grid-cols-4">
                <SummaryMini
                  label="Mejor estrategia"
                  value={STRATEGY_LABELS[comparison.mejor_estrategia] || comparison.mejor_estrategia}
                  helper={`Ahorro ${formatCurrency(comparison.ahorro_estimado)}`}
                />
                <SummaryMini label="Precio actual" value={formatCurrency(comparison.precio_actual)} helper="Base de comparacion" />
                <SummaryMini label="Precio futuro" value={formatCurrency(comparison.precio_proyectado_horizonte)} helper={`Horizonte ${comparison.horizonte_meses} meses`} />
                <SummaryMini label="Confiabilidad" value={comparison.confiabilidad} helper="Lectura metodologica del forecast" />
              </Box>

              <Alert severity="info">
                {comparison.justificacion}
              </Alert>

              <Box className="grid gap-2">
                {comparison.estrategias.map((strategy) => (
                  <Box key={strategy.nombre} className="grid gap-2 rounded-xl border border-slate-200 p-3 md:grid-cols-[1.2fr_.8fr_.8fr] md:items-center">
                    <Box>
                      <Typography fontWeight={800}>{STRATEGY_LABELS[strategy.nombre] || strategy.nombre}</Typography>
                      <Typography color="text.secondary" fontSize={13}>
                        {strategy.descripcion}
                      </Typography>
                    </Box>
                    <Typography fontWeight={700}>Costo: {formatCurrency(strategy.costo_estimado)}</Typography>
                    <Typography color="text.secondary" fontWeight={800}>
                      Riesgo: {strategy.riesgo}
                    </Typography>
                  </Box>
                ))}
              </Box>

              {comparison.advertencias?.length ? (
                <Alert severity="warning">
                  <Box className="grid gap-1">
                    {comparison.advertencias.map((warning, index) => (
                      <Typography key={`${warning}-${index}`} fontSize={13}>
                        {warning}
                      </Typography>
                    ))}
                  </Box>
                </Alert>
              ) : null}
            </Box>
          ) : null}

          {!recommendation && !comparison ? (
            <Alert severity="info">
              La recomendación contextual considera fase de obra, fecha u horizonte y tolerancia al riesgo. La comparación de
              estrategias permite revisar alternativas económicas para el mismo material.
            </Alert>
          ) : null}
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
