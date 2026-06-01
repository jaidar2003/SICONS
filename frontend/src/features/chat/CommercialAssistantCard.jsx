import { Alert, Box, Button, Card, CardContent, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { generateCommercialProposal, interpretCommercialNeed } from "./chat.api.js";

const PHASES = [
  { value: "estructura", label: "Estructura" },
  { value: "terminaciones", label: "Terminaciones" },
  { value: "impermeabilizacion", label: "Impermeabilización" },
  { value: "general", label: "General" },
];

const RISK_LEVELS = [
  { value: "baja", label: "Baja" },
  { value: "media", label: "Media" },
  { value: "alta", label: "Alta" },
];

const DECISION_LABELS = {
  COMPRAR_AHORA: "Comprar ahora",
  POSTERGAR: "Postergar",
  ESCALONAR: "Escalonar",
  SIN_VENTAJA_CLARA: "Sin ventaja clara",
};

const SUPPORTED_PRODUCT_KEYS = new Set(["cemento-portland", "pastina", "membrana-megaflex"]);
const PROVIDER_LABELS = {
  facultad: "API de la facultad",
  claude: "Claude",
};

function materialKey(nombre) {
  return String(nombre || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function createEmptyDraft() {
  return {
    materialId: "",
    quantity: "",
    phase: "general",
    targetDate: "",
    horizon: "3",
    budget: "",
    risk: "media",
    request: "",
  };
}

export function CommercialAssistantCard({ materiales, token, showPrices }) {
  const commercialMaterials = useMemo(
    () => materiales.filter((material) => SUPPORTED_PRODUCT_KEYS.has(materialKey(material.nombre))),
    [materiales]
  );
  const [need, setNeed] = useState("");
  const [draft, setDraft] = useState(createEmptyDraft);
  const [interpretation, setInterpretation] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [loadingInterpretation, setLoadingInterpretation] = useState(false);
  const [loadingProposal, setLoadingProposal] = useState(false);
  const [error, setError] = useState("");

  async function handleInterpret() {
    const trimmed = need.trim();
    if (!trimmed) {
      setError("Describí la necesidad de compra antes de interpretar.");
      return;
    }
    setError("");
    setProposal(null);
    setLoadingInterpretation(true);
    try {
      const result = await interpretCommercialNeed({ necesidad: trimmed }, token);
      setInterpretation(result);
      setDraft({
        materialId: result.material_id ? String(result.material_id) : "",
        quantity: result.cantidad ?? "",
        phase: result.fase_obra || "general",
        targetDate: result.fecha_objetivo_uso || "",
        horizon: result.horizonte_meses ? String(result.horizonte_meses) : "3",
        budget: result.presupuesto_maximo ?? "",
        risk: result.tolerancia_riesgo || "media",
        request: trimmed,
      });
    } catch (interpretError) {
      setError(interpretError.message);
    } finally {
      setLoadingInterpretation(false);
    }
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
    setProposal(null);
  }

  async function handleGenerate() {
    const quantity = Number(draft.quantity);
    if (!draft.materialId || !Number.isFinite(quantity) || quantity <= 0) {
      setError("Validá producto y cantidad antes de generar la propuesta.");
      return;
    }
    setError("");
    setLoadingProposal(true);
    try {
      const payload = {
        material_id: Number(draft.materialId),
        cantidad: quantity,
        fase_obra: draft.phase,
        tolerancia_riesgo: draft.risk,
        solicitud_original: draft.request,
        ...(draft.targetDate ? { fecha_objetivo_uso: draft.targetDate } : { horizonte_meses: Number(draft.horizon) }),
      };
      const budget = Number(draft.budget);
      if (Number.isFinite(budget) && budget > 0) payload.presupuesto_maximo = budget;
      setProposal(await generateCommercialProposal(payload, token));
    } catch (proposalError) {
      setError(proposalError.message);
    } finally {
      setLoadingProposal(false);
    }
  }

  if (!showPrices) {
    return (
      <Card className="mt-3">
        <CardContent>
          <SectionHeader title="Asistente de compra IA" description="Convierte una necesidad de obra en una propuesta de compra explicable." />
          <Alert severity="info">Activá la vista de precios para generar presupuestos de compra.</Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Asistente de compra IA"
          description="Describí la necesidad de compra. La IA propone una interpretación editable; BuildWise calcula la propuesta solo con datos validados."
        />
        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {!commercialMaterials.length ? (
            <Alert severity="warning">No hay productos del MVP disponibles para presupuestación de compra.</Alert>
          ) : null}

          <TextField
            multiline
            minRows={3}
            label="Necesidad de compra"
            value={need}
            onChange={(event) => setNeed(event.target.value)}
            placeholder="Ej.: En septiembre impermeabilizo una terraza y necesito 30 unidades de Membrana Megaflex. ¿Me conviene comprar ahora?"
            inputProps={{ maxLength: 1500 }}
          />
          <Box>
            <Button variant="contained" onClick={handleInterpret} disabled={loadingInterpretation || !need.trim() || !commercialMaterials.length}>
              {loadingInterpretation ? "Interpretando..." : "Interpretar con IA"}
            </Button>
          </Box>

          {interpretation ? (
            <Box className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <Typography variant="h3">Validar datos interpretados</Typography>
              {interpretation.datos_faltantes.length ? (
                <Alert severity="warning">
                  Faltan o requieren corrección: {interpretation.datos_faltantes.join(", ")}.
                </Alert>
              ) : (
                <Alert severity="info">Revisá y corregí los campos detectados antes de calcular; la validación humana es obligatoria.</Alert>
              )}
              <Box className="grid gap-3 md:grid-cols-3">
                <FormControl size="small">
                  <InputLabel id="commercial-material">Producto</InputLabel>
                  <Select
                    labelId="commercial-material"
                    label="Producto"
                    value={draft.materialId}
                    onChange={(event) => updateDraft("materialId", String(event.target.value))}
                  >
                    {commercialMaterials.map((material) => (
                      <MenuItem key={material.id} value={String(material.id)}>
                        {material.nombre}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  size="small"
                  label="Cantidad"
                  type="number"
                  value={draft.quantity}
                  onChange={(event) => updateDraft("quantity", event.target.value)}
                  inputProps={{ min: 0, step: "any" }}
                />
                <FormControl size="small">
                  <InputLabel id="commercial-phase">Fase de obra</InputLabel>
                  <Select labelId="commercial-phase" label="Fase de obra" value={draft.phase} onChange={(event) => updateDraft("phase", event.target.value)}>
                    {PHASES.map((phase) => (
                      <MenuItem key={phase.value} value={phase.value}>{phase.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  size="small"
                  label="Fecha objetivo (opcional)"
                  type="date"
                  value={draft.targetDate}
                  onChange={(event) => updateDraft("targetDate", event.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
                <TextField
                  size="small"
                  label="Horizonte sin fecha"
                  type="number"
                  value={draft.horizon}
                  disabled={Boolean(draft.targetDate)}
                  onChange={(event) => updateDraft("horizon", event.target.value)}
                  inputProps={{ min: 1, max: 12 }}
                />
                <TextField
                  size="small"
                  label="Presupuesto máximo (opcional)"
                  type="number"
                  value={draft.budget}
                  onChange={(event) => updateDraft("budget", event.target.value)}
                  inputProps={{ min: 0, step: "any" }}
                />
                <FormControl size="small">
                  <InputLabel id="commercial-risk">Tolerancia al riesgo</InputLabel>
                  <Select labelId="commercial-risk" label="Tolerancia al riesgo" value={draft.risk} onChange={(event) => updateDraft("risk", event.target.value)}>
                    {RISK_LEVELS.map((risk) => (
                      <MenuItem key={risk.value} value={risk.value}>{risk.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <Button variant="contained" color="secondary" onClick={handleGenerate} disabled={loadingProposal}>
                  {loadingProposal ? "Generando..." : "Validar y generar propuesta"}
                </Button>
              </Box>
            </Box>
          ) : null}

          {proposal ? (
            <Box className="grid gap-3 rounded-xl border border-teal-200 bg-white p-4">
              <Typography variant="h3">Propuesta de compra</Typography>
              <Box className="grid gap-3 md:grid-cols-4">
                <ProposalValue label="Total actual" value={proposal.total_actual === null ? "-" : formatCurrency(proposal.total_actual)} />
                <ProposalValue label="Total proyectado" value={proposal.total_proyectado === null ? "-" : formatCurrency(proposal.total_proyectado)} />
                <ProposalValue label="Diferencia estimada" value={proposal.diferencia_estimada === null ? "-" : formatCurrency(proposal.diferencia_estimada)} />
                <ProposalValue label="Decisión" value={DECISION_LABELS[proposal.decision] || proposal.decision} />
              </Box>
              <Alert severity="success">
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{proposal.propuesta}</Typography>
              </Alert>
              <Typography variant="body2" color="text.secondary">
                Confianza: {proposal.confiabilidad}{proposal.mape === null ? "" : ` / MAPE ${formatNumber(proposal.mape)}%`}. {proposal.justificacion}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Fuente de decisión: {proposal.fuente_decision || "backend_deterministico"}. Redacción: {proposal.propuesta_generada_por || "llm_validado"}.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                IA usada: {PROVIDER_LABELS[proposal.proveedor_ia] || proposal.proveedor_ia || "no disponible"}
                {proposal.fallback_usado ? " (fallback activado)" : ""}.
              </Typography>
              {proposal.advertencias.length ? <Alert severity="warning">{proposal.advertencias.join(" ")}</Alert> : null}
            </Box>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

function ProposalValue({ label, value }) {
  return (
    <Box className="rounded-lg border border-slate-200 p-3">
      <Typography variant="body2" color="text.secondary" fontWeight={800}>{label}</Typography>
      <Typography mt={0.5} fontWeight={800}>{value ?? "-"}</Typography>
    </Box>
  );
}
