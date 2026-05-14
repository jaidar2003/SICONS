import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { generateOperationalRecommendation } from "./pricing.api.js";

const DEFAULT_ROWS = [
  { match: "cemento", cantidad: "100", criticidad: "alta" },
  { match: "pastina", cantidad: "40", criticidad: "media" },
  { match: "membrana", cantidad: "20", criticidad: "baja" },
];

const ACTION_META = {
  COMPRAR_AHORA: {
    label: "Comprar ahora",
    color: "error",
    helper: "Conviene anticipar la compra.",
    bg: "#fef2f2",
    border: "#fecaca",
  },
  COMPRA_PARCIAL: {
    label: "Compra parcial",
    color: "warning",
    helper: "Conviene cubrir una parte y postergar el resto.",
    bg: "#fffbeb",
    border: "#fde68a",
  },
  POSTERGAR: {
    label: "Postergar",
    color: "success",
    helper: "No es prioridad comprar ahora.",
    bg: "#f0fdf4",
    border: "#bbf7d0",
  },
};

const CRITICIDAD_LABELS = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
};

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function buildDefaultRows(materiales) {
  const usedIds = new Set();
  const rows = DEFAULT_ROWS.map((defaultRow, index) => {
    const material = materiales.find(
      (candidate) => !usedIds.has(candidate.id) && normalize(candidate.nombre).includes(defaultRow.match)
    );
    if (material) usedIds.add(material.id);
    return {
      id: `decision-${index}`,
      materialId: material ? String(material.id) : "",
      cantidad: defaultRow.cantidad,
      criticidad: defaultRow.criticidad,
    };
  });

  if (rows.every((row) => row.materialId)) return rows;

  return rows.map((row, index) => {
    if (row.materialId) return row;
    const fallback = materiales.find((candidate) => !usedIds.has(candidate.id));
    if (fallback) usedIds.add(fallback.id);
    return {
      ...row,
      materialId: fallback ? String(fallback.id) : "",
      cantidad: row.cantidad || String(index === 0 ? 100 : 20),
    };
  });
}

function actionMeta(action) {
  return ACTION_META[action] || {
    label: action || "Revisar",
    color: "default",
    helper: "Revisar manualmente.",
    bg: "#f8fafc",
    border: "#cbd5e1",
  };
}

export function FinalDecisionCard({ materiales, forecastHorizon, token, showPrices }) {
  const [rows, setRows] = useState([]);
  const [budgetInput, setBudgetInput] = useState("180000");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!materiales.length || rows.length) return;
    setRows(buildDefaultRows(materiales));
  }, [materiales, rows.length]);

  const materialById = useMemo(
    () => new Map(materiales.map((material) => [String(material.id), material])),
    [materiales]
  );

  const payloadItems = useMemo(
    () =>
      rows
        .filter((row) => row.materialId && Number(row.cantidad) > 0)
        .map((row) => ({
          material_id: Number(row.materialId),
          cantidad_objetivo: Number(row.cantidad),
          criticidad: row.criticidad,
        })),
    [rows]
  );

  const groupedItems = useMemo(() => {
    const groups = {
      COMPRAR_AHORA: [],
      COMPRA_PARCIAL: [],
      POSTERGAR: [],
    };
    for (const item of result?.items || []) {
      const key = groups[item.accion_recomendada] ? item.accion_recomendada : "POSTERGAR";
      groups[key].push(item);
    }
    return groups;
  }, [result]);

  const firstDecision = useMemo(() => {
    if (!result?.items?.length) return null;
    return (
      result.items.find((item) => item.accion_recomendada === "COMPRAR_AHORA") ||
      result.items.find((item) => item.accion_recomendada === "COMPRA_PARCIAL") ||
      result.items[0]
    );
  }, [result]);

  function updateRow(rowId, field, value) {
    setRows((current) => current.map((row) => (row.id === rowId ? { ...row, [field]: value } : row)));
  }

  async function handleGenerate() {
    setError("");
    setResult(null);

    const presupuesto = Number(budgetInput);
    if (!Number.isFinite(presupuesto) || presupuesto <= 0) {
      setError("Ingresá un presupuesto mayor a cero.");
      return;
    }
    if (!payloadItems.length) {
      setError("Seleccioná al menos un material con cantidad válida.");
      return;
    }

    setLoading(true);
    try {
      const response = await generateOperationalRecommendation(
        {
          presupuesto_total: presupuesto,
          horizonte_meses: forecastHorizon,
          materiales: payloadItems,
        },
        token
      );
      setResult(response);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
          <SectionHeader
            title="Decisión final de compra"
            description="Recomendación operativa basada en forecast, criticidad y presupuesto."
          />
          <Alert severity="info">Activá la vista de precios para generar la recomendación operativa.</Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-3 overflow-hidden border border-slate-200">
      <CardContent>
        <SectionHeader
          title="Decisión final de compra"
          description="Elegí materiales, cantidades y presupuesto. El sistema devuelve qué comprar ahora, qué postergar y por qué."
          badge="HU28b"
          action={
            <Button variant="contained" onClick={handleGenerate} disabled={loading}>
              {loading ? "Calculando..." : "Generar decisión"}
            </Button>
          }
        />

        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Box className="grid gap-3 lg:grid-cols-[220px_1fr] lg:items-start">
            <TextField
              label="Presupuesto disponible"
              type="number"
              value={budgetInput}
              onChange={(event) => setBudgetInput(event.target.value)}
              inputProps={{ min: 0, step: "any" }}
              helperText={`Horizonte activo: ${forecastHorizon} meses`}
            />

            <Box className="grid gap-3 md:grid-cols-3">
              {rows.map((row, index) => {
                const material = materialById.get(row.materialId);
                return (
                  <Box key={row.id} className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <Typography color="text.secondary" fontSize={12} fontWeight={900}>
                      Material {index + 1}
                    </Typography>
                    <FormControl size="small">
                      <InputLabel id={`final-material-${row.id}`}>Material</InputLabel>
                      <Select
                        labelId={`final-material-${row.id}`}
                        label="Material"
                        value={row.materialId}
                        onChange={(event) => updateRow(row.id, "materialId", String(event.target.value))}
                      >
                        {materiales.map((option) => (
                          <MenuItem key={option.id} value={String(option.id)}>
                            {option.nombre}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      size="small"
                      label={`Cantidad${material?.unidad_base ? ` (${material.unidad_base})` : ""}`}
                      type="number"
                      value={row.cantidad}
                      onChange={(event) => updateRow(row.id, "cantidad", event.target.value)}
                      inputProps={{ min: 0, step: "any" }}
                    />
                    <FormControl size="small">
                      <InputLabel id={`final-criticality-${row.id}`}>Criticidad</InputLabel>
                      <Select
                        labelId={`final-criticality-${row.id}`}
                        label="Criticidad"
                        value={row.criticidad}
                        onChange={(event) => updateRow(row.id, "criticidad", String(event.target.value))}
                      >
                        <MenuItem value="alta">Alta</MenuItem>
                        <MenuItem value="media">Media</MenuItem>
                        <MenuItem value="baja">Baja</MenuItem>
                      </Select>
                    </FormControl>
                  </Box>
                );
              })}
            </Box>
          </Box>

          {loading ? (
            <Box className="flex justify-center rounded-xl border border-slate-200 bg-slate-50 py-5">
              <CircularProgress size={28} />
            </Box>
          ) : null}

          {!result && !loading ? (
            <Alert severity="info">
              Usá los valores precargados para una demo rápida con presupuesto restrictivo. La salida prioriza ahorro esperado ajustado por criticidad y respeta el presupuesto.
            </Alert>
          ) : null}

          {result ? (
            <>
              <Box className="rounded-2xl border border-slate-200 bg-white p-4">
                <Box className="grid gap-3 lg:grid-cols-[1.2fr_.8fr_.8fr_.8fr] lg:items-center">
                  <Box>
                    <Typography variant="overline" color="text.secondary">
                      Recomendación operativa
                    </Typography>
                    <Typography variant="h2" lineHeight={1.1} mt={0.5}>
                      {firstDecision ? actionMeta(firstDecision.accion_recomendada).label : "Revisar plan"}
                    </Typography>
                    <Typography color="text.secondary" variant="body2" mt={0.75}>
                      {result.decision_resumen}
                    </Typography>
                  </Box>
                  <SummaryMini label="Presupuesto usado" value={formatCurrency(result.presupuesto_utilizado)} helper={`De ${formatCurrency(result.presupuesto_total)}`} />
                  <SummaryMini label="Presupuesto restante" value={formatCurrency(result.presupuesto_restante)} helper={`Calculado el ${result.fecha_calculo}`} />
                  <SummaryMini label="Ahorro estimado" value={formatCurrency(result.ahorro_total_estimado)} helper="Frente a postergar compra" />
                </Box>
              </Box>

              <Box className="grid gap-3 md:grid-cols-3">
                <ActionColumn title="Comprar ahora" items={groupedItems.COMPRAR_AHORA} action="COMPRAR_AHORA" materialById={materialById} />
                <ActionColumn title="Compra parcial" items={groupedItems.COMPRA_PARCIAL} action="COMPRA_PARCIAL" materialById={materialById} />
                <ActionColumn title="Postergar" items={groupedItems.POSTERGAR} action="POSTERGAR" materialById={materialById} />
              </Box>

              <Box className="grid gap-3 lg:grid-cols-[1fr_1fr]">
                <Alert severity="success">
                  <Typography fontWeight={900} mb={0.75}>
                    Por qué recomienda esto
                  </Typography>
                  <Box className="grid gap-1">
                    {result.items.map((item) => (
                      <Typography key={item.material_id} variant="body2">
                        {item.explicacion}
                      </Typography>
                    ))}
                  </Box>
                </Alert>

                <Alert severity={result.advertencias?.length ? "warning" : "info"}>
                  <Typography fontWeight={900} mb={0.75}>
                    Supuestos y confianza
                  </Typography>
                  <Box className="grid gap-1">
                    {result.supuestos?.map((supuesto, index) => (
                      <Typography key={`${supuesto}-${index}`} variant="body2">
                        {supuesto}
                      </Typography>
                    ))}
                    {result.advertencias?.map((warning, index) => (
                      <Typography key={`${warning}-${index}`} variant="body2">
                        {warning}
                      </Typography>
                    ))}
                  </Box>
                </Alert>
              </Box>
            </>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

function ActionColumn({ title, items, action, materialById }) {
  const meta = actionMeta(action);
  return (
    <Box
      className="grid content-start gap-2 rounded-2xl border p-3"
      sx={{ backgroundColor: meta.bg, borderColor: meta.border }}
    >
      <Box className="flex items-center justify-between gap-2">
        <Typography fontWeight={900}>{title}</Typography>
        <Chip color={meta.color} label={items.length} size="small" />
      </Box>
      <Typography color="text.secondary" variant="body2">
        {meta.helper}
      </Typography>
      {items.length ? (
        items.map((item) => <DecisionItem key={item.material_id} item={item} material={materialById.get(String(item.material_id))} />)
      ) : (
        <Box className="rounded-xl border border-dashed border-slate-300 bg-white/70 p-3">
          <Typography color="text.secondary" variant="body2">
            Sin materiales en esta acción.
          </Typography>
        </Box>
      )}
    </Box>
  );
}

function DecisionItem({ item, material }) {
  return (
    <Box className="rounded-xl border border-white bg-white p-3 shadow-sm">
      <Box className="flex items-start justify-between gap-2">
        <Box>
          <Typography fontWeight={900}>{material?.nombre || item.material_key}</Typography>
          <Typography color="text.secondary" variant="body2">
            Criticidad {CRITICIDAD_LABELS[item.criticidad] || item.criticidad}
          </Typography>
        </Box>
        <Tooltip title="Lectura simple del error histórico y calibración del forecast.">
          <Chip label={`Confianza ${item.confianza}`} size="small" variant="outlined" />
        </Tooltip>
      </Box>
      <Box className="mt-2 grid grid-cols-2 gap-2">
        <SmallMetric label="Ahora" value={formatNumber(item.cantidad_comprar_ahora, 2)} />
        <SmallMetric label="Postergar" value={formatNumber(item.cantidad_postergar, 2)} />
        <SmallMetric label="Impacto" value={formatCurrency(item.impacto_economico_estimado)} />
        <SmallMetric label="%" value={`${formatNumber(item.impacto_economico_pct)}%`} />
      </Box>
    </Box>
  );
}

function SummaryMini({ label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 p-3">
      <Typography color="text.secondary" fontSize={12} fontWeight={900}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} fontSize={24} fontWeight={900} lineHeight={1.05}>
        {value}
      </Typography>
      <Typography color="text.secondary" fontSize={13} mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}

function SmallMetric({ label, value }) {
  return (
    <Box className="rounded-lg bg-slate-50 px-2 py-1.5">
      <Typography color="text.secondary" fontSize={11} fontWeight={900}>
        {label}
      </Typography>
      <Typography fontSize={14} fontWeight={900}>
        {value}
      </Typography>
    </Box>
  );
}
