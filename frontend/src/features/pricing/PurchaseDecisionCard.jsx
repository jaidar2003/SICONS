import { Alert, Box, Button, Card, CardContent, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { comparePurchaseStrategies, recommendPurchase } from "./pricing.api.js";

const DECISION_LABELS = {
  COMPRAR_AHORA: "Comprar ahora",
  ESPERAR: "Esperar",
  MONITOREAR: "Monitorear",
  COMPRAR_AHORA_AL_HORIZONTE: "Comprar ahora al horizonte",
  ESPERAR_AL_HORIZONTE: "Esperar al horizonte",
};

const STRATEGY_LABELS = {
  COMPRAR_AHORA: "Comprar ahora",
  ESPERAR_AL_HORIZONTE: "Esperar al horizonte",
  COMPRA_PARCIAL: "Compra parcial",
};

export function PurchaseDecisionCard({ materiales, selectedMaterialId, forecastHorizon, token, showPrices }) {
  const [materialId, setMaterialId] = useState(selectedMaterialId || "");
  const [quantityInput, setQuantityInput] = useState("100");
  const [criticidad, setCriticidad] = useState("media");
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

  const selectedMaterial = useMemo(
    () => materiales.find((material) => String(material.id) === String(materialId)),
    [materialId, materiales]
  );

  const quantity = Number(quantityInput);
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
      const result = await recommendPurchase(
        {
          horizonte_meses: forecastHorizon,
          criticidad,
          cantidad_objetivo: quantity,
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
          horizonte_meses: forecastHorizon,
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
          description="Recomendacion simple y comparacion de estrategias de compra."
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
          description="Convierte el forecast en una recomendacion operativa y compara estrategias de compra sobre un material puntual."
        />

        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Box className="grid gap-3 lg:grid-cols-[1.2fr_.8fr_.8fr] lg:items-end">
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

            <TextField
              size="small"
              label="Cantidad objetivo"
              type="number"
              value={quantityInput}
              onChange={(event) => setQuantityInput(event.target.value)}
              inputProps={{ min: 0, step: "any" }}
            />

            <FormControl size="small">
              <InputLabel id="decision-criticidad">Criticidad</InputLabel>
              <Select
                labelId="decision-criticidad"
                label="Criticidad"
                value={criticidad}
                onChange={(event) => setCriticidad(String(event.target.value))}
              >
                <MenuItem value="alta">Alta</MenuItem>
                <MenuItem value="media">Media</MenuItem>
                <MenuItem value="baja">Baja</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <Box className="grid gap-3 lg:grid-cols-[1fr_.7fr_.7fr] lg:items-end">
            <TextField
              size="small"
              label="Compra inmediata"
              type="number"
              value={comparisonShare}
              onChange={(event) => setComparisonShare(event.target.value)}
              inputProps={{ min: 0, max: 1, step: "0.05" }}
              helperText="0 = esperar todo, 1 = comprar todo ahora."
            />
            <Button variant="contained" color="primary" onClick={handleRecommend} disabled={loadingRecommendation}>
              {loadingRecommendation ? "Calculando..." : "Calcular recomendacion"}
            </Button>
            <Button variant="outlined" color="secondary" onClick={handleCompare} disabled={loadingComparison}>
              {loadingComparison ? "Comparando..." : "Comparar estrategias"}
            </Button>
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
                  helper={`Criticidad ${recommendation.criticidad}`}
                />
                <SummaryMini label="Confiabilidad" value={recommendation.confiabilidad} helper="Lectura metodologica del forecast" />
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
              La recomendacion simple responde "que conviene hacer" y la comparacion de estrategias muestra por que. Son dos
              capas distintas del modulo de decisiones.
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
