import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { askChatQuestion, generateCommercialProposal, interpretCommercialNeed } from "./chat.api.js";

const PROVIDER_LABELS = {
  facultad: "API de la facultad",
  claude: "Claude",
};
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
const COMMERCIAL_DRAFT_STORAGE_KEY = "buildwise.chat.commercialDraft.v1";

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

function initialMessage(isAdmin) {
  return {
    role: "assistant",
    text: isAdmin
      ? "Podés consultarme precios, forecast, recomendaciones, estrategias de compra, presupuestos, prioridades y optimización. Las operaciones administrativas requieren confirmación."
      : "Podés consultarme precios, forecast, recomendaciones, estrategias de compra, presupuestos, prioridades y optimización.",
  };
}

function looksLikePurchaseNeed(text) {
  const normalized = String(text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  const hasPurchaseIntent = /\b(comprar|compra|presupuesto|cotizar|cotizacion|necesito|obra|propuesta)\b/.test(normalized);
  const hasMaterial = /\b(cemento|pastina|membrana|megaflex|material|materiales)\b/.test(normalized);
  const hasQuantity = /\b\d+([,.]\d+)?\b/.test(normalized);
  return hasPurchaseIntent && hasMaterial && hasQuantity;
}

export function ChatCard({ token, selectedMaterial, forecastHorizon, isAdmin, materiales = [], showPrices = true }) {
  const commercialMaterials = useMemo(
    () => materiales.filter((material) => SUPPORTED_PRODUCT_KEYS.has(materialKey(material.nombre))),
    [materiales]
  );
  const draftStorageKey = `${COMMERCIAL_DRAFT_STORAGE_KEY}.${selectedMaterial?.id ?? "none"}`;
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([initialMessage(isAdmin)]);
  const [draft, setDraft] = useState(createEmptyDraft);
  const [interpretation, setInterpretation] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [commercialFlowReady, setCommercialFlowReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [error, setError] = useState("");
  const draftQuantity = Number(draft.quantity);
  const proposalDisabled =
    proposalLoading ||
    !commercialMaterials.length ||
    !draft.materialId ||
    !Number.isFinite(draftQuantity) ||
    draftQuantity <= 0 ||
    (!draft.targetDate && (!Number(draft.horizon) || Number(draft.horizon) < 1 || Number(draft.horizon) > 12));

  useEffect(() => {
    setCommercialFlowReady(false);
    try {
      const stored = window.localStorage.getItem(draftStorageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === "object") {
          setDraft(parsed.draft ? { ...createEmptyDraft(), ...parsed.draft } : createEmptyDraft());
          setInterpretation(parsed.interpretation || null);
          setProposal(parsed.proposal || null);
        } else {
          setDraft(createEmptyDraft());
          setInterpretation(null);
          setProposal(null);
        }
      } else {
        setDraft(createEmptyDraft());
        setInterpretation(null);
        setProposal(null);
      }
    } catch {
      window.localStorage.removeItem(draftStorageKey);
      setDraft(createEmptyDraft());
      setInterpretation(null);
      setProposal(null);
    } finally {
      setCommercialFlowReady(true);
    }
  }, [draftStorageKey]);

  useEffect(() => {
    if (!commercialFlowReady) return;
    const payload = JSON.stringify({
      draft,
      interpretation,
      proposal,
    });
    window.localStorage.setItem(draftStorageKey, payload);
  }, [commercialFlowReady, draft, interpretation, proposal, draftStorageKey]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setQuestion("");
    setError("");
    setProposal(null);
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setLoading(true);
    try {
      if (looksLikePurchaseNeed(trimmed)) {
        if (!showPrices) {
          setMessages((current) => [
            ...current,
            {
              role: "assistant",
              text: "Para generar una propuesta de compra tenés que activar la vista de precios.",
              rejected: true,
            },
          ]);
          return;
        }
        const result = await interpretCommercialNeed({ necesidad: trimmed }, token);
        setInterpretation(result);
        setDraft({
          materialId: result.material_id ? String(result.material_id) : selectedMaterial?.id ? String(selectedMaterial.id) : "",
          quantity: result.cantidad ?? "",
          phase: result.fase_obra || "general",
          targetDate: result.fecha_objetivo_uso || "",
          horizon: result.horizonte_meses ? String(result.horizonte_meses) : String(forecastHorizon),
          budget: result.presupuesto_maximo ?? "",
          risk: result.tolerancia_riesgo || "media",
          request: trimmed,
        });
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            text: "Detecté una necesidad de compra. Revisá los datos interpretados y confirmá la propuesta desde el panel de validación.",
            provider: result.proveedor_ia,
            fallbackUsed: Boolean(result.fallback_usado),
          },
        ]);
        return;
      }

      const historial = messages
        .slice(1)
        .filter((message) => !message.rejected)
        .slice(-8)
        .map((message) => ({ role: message.role, content: message.text }));
      const result = await askChatQuestion(
        {
          pregunta: trimmed,
          material_id: selectedMaterial?.id ?? null,
          horizonte_meses: forecastHorizon,
          historial,
        },
        token
      );
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: result.respuesta,
          provider: result.proveedor_ia,
          fallbackUsed: Boolean(result.fallback_usado),
          contextUsed: Boolean(result.contexto_usado),
          intent: result.tipo_intencion,
          sources: result.fuentes_recuperadas || [],
          resolvedMaterial: result.material_resuelto,
          resolvedHorizon: result.horizonte_resuelto,
          rejected: !result.aceptada,
        },
      ]);
    } catch (chatError) {
      setError(chatError.message);
    } finally {
      setLoading(false);
    }
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
    setProposal(null);
  }

  function resetCommercialFlow() {
    setDraft(createEmptyDraft());
    setInterpretation(null);
    setProposal(null);
    setError("");
    window.localStorage.removeItem(draftStorageKey);
  }

  async function handleGenerateProposal() {
    const quantity = Number(draft.quantity);
    if (proposalDisabled) {
      setError("Validá producto y cantidad antes de generar la propuesta.");
      return;
    }
    setError("");
    setProposalLoading(true);
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
      const result = await generateCommercialProposal(payload, token);
      setProposal(result);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: result.propuesta,
          provider: result.proveedor_ia,
          fallbackUsed: Boolean(result.fallback_usado),
          contextUsed: true,
          intent: "PRESUPUESTO",
          sources: ["presupuestacion.propuesta", result.fuente_decision || "backend_deterministico"],
          resolvedMaterial: result.producto_nombre,
          resolvedHorizon: result.horizonte_meses,
        },
      ]);
    } catch (proposalError) {
      setError(proposalError.message);
    } finally {
      setProposalLoading(false);
    }
  }

  return (
    <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
      <CardContent>
        <SectionHeader
          title="Asistente BuildWise"
          description={`Opera con datos calculados de ${selectedMaterial?.nombre || "los materiales"} a ${forecastHorizon} meses. Las consultas externas se rechazan antes de llamar al proveedor de IA.`}
        />

        {error ? <Alert severity="error" className="mb-3">{error}</Alert> : null}

        <Box className="mb-4 flex min-h-[300px] flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          {messages.map((message, index) => (
            <Box
              key={`${message.role}-${index}`}
              className={`max-w-[85%] rounded-xl px-4 py-3 ${message.role === "user" ? "ml-auto bg-teal-700 text-white" : "bg-white text-slate-800 shadow-sm"}`}
            >
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {message.text}
              </Typography>
              {message.role === "assistant" && !message.rejected ? (
                <Box className="mt-2 flex flex-wrap gap-1.5">
                  <Chip
                    label={`IA usada: ${PROVIDER_LABELS[message.provider] || message.provider || "no disponible"}`}
                    size="small"
                    variant="outlined"
                    sx={{ fontWeight: 800 }}
                  />
                  {message.fallbackUsed ? <Chip label="Fallback activado" size="small" color="warning" sx={{ fontWeight: 800 }} /> : null}
                  {message.intent ? <Chip label={`Intención: ${message.intent}`} size="small" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {message.contextUsed ? <Chip label="RAG backend" size="small" color="success" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {message.resolvedMaterial ? <Chip label={`Material: ${message.resolvedMaterial}`} size="small" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {message.resolvedHorizon ? <Chip label={`Horizonte: ${message.resolvedHorizon} meses`} size="small" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {(message.sources || []).map((source) => (
                    <Chip key={source} label={source} size="small" variant="outlined" sx={{ fontWeight: 800 }} />
                  ))}
                </Box>
              ) : null}
              {message.rejected ? (
                <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                  Consulta fuera del alcance habilitado.
                </Typography>
              ) : null}
            </Box>
          ))}
          {loading ? (
            <Box className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-slate-600 shadow-sm">
              <CircularProgress size={16} />
              <Typography variant="body2">Consultando asistente...</Typography>
            </Box>
          ) : null}
        </Box>

        {interpretation ? (
          <Box className="mb-4 grid gap-3 rounded-xl border border-teal-200 bg-white p-4">
            <Box className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <Box>
                <Typography variant="h3">Validar necesidad de compra</Typography>
                <Typography variant="body2" color="text.secondary" mt={0.5}>
                  La IA interpreta el pedido; BuildWise calcula la propuesta solo con los datos confirmados por el usuario.
                </Typography>
              </Box>
              <Button variant="outlined" color="secondary" onClick={resetCommercialFlow} disabled={proposalLoading}>
                Cancelar
              </Button>
            </Box>
            {interpretation.datos_faltantes?.length ? (
              <Alert severity="warning">Faltantes detectados inicialmente: {interpretation.datos_faltantes.join(", ")}.</Alert>
            ) : (
              <Alert severity="info">Revisá los campos antes de generar la propuesta comercial.</Alert>
            )}
            {!commercialMaterials.length ? (
              <Alert severity="warning">No hay productos del MVP disponibles para presupuestación de compra.</Alert>
            ) : null}
            <Box className="flex flex-wrap gap-1.5">
              <Chip label="Interpretado por IA" size="small" color="info" variant="outlined" sx={{ fontWeight: 800 }} />
              <Chip
                label={`IA usada: ${PROVIDER_LABELS[interpretation.proveedor_ia] || interpretation.proveedor_ia || "no disponible"}`}
                size="small"
                variant="outlined"
                sx={{ fontWeight: 800 }}
              />
              {interpretation.fallback_usado ? <Chip label="Fallback activado" size="small" color="warning" sx={{ fontWeight: 800 }} /> : null}
            </Box>
            <Typography variant="body2" fontWeight={900} color="text.secondary">
              Datos confirmados por el usuario
            </Typography>
            <Box className="grid gap-3 md:grid-cols-3">
              <TextField select size="small" label="Producto" value={draft.materialId} onChange={(event) => updateDraft("materialId", String(event.target.value))}>
                {commercialMaterials.map((material) => (
                  <MenuItem key={material.id} value={String(material.id)}>
                    {material.nombre}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                label="Cantidad"
                type="number"
                value={draft.quantity}
                onChange={(event) => updateDraft("quantity", event.target.value)}
                inputProps={{ min: 0, step: "any" }}
              />
              <TextField select size="small" label="Fase de obra" value={draft.phase} onChange={(event) => updateDraft("phase", event.target.value)}>
                {PHASES.map((phase) => (
                  <MenuItem key={phase.value} value={phase.value}>
                    {phase.label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                label="Fecha objetivo"
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
                label="Presupuesto máximo"
                type="number"
                value={draft.budget}
                onChange={(event) => updateDraft("budget", event.target.value)}
                inputProps={{ min: 0, step: "any" }}
              />
              <TextField select size="small" label="Tolerancia al riesgo" value={draft.risk} onChange={(event) => updateDraft("risk", event.target.value)}>
                {RISK_LEVELS.map((risk) => (
                  <MenuItem key={risk.value} value={risk.value}>
                    {risk.label}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
            {proposalDisabled ? (
              <Alert severity="info">Completá producto, cantidad y fecha u horizonte válido para generar la propuesta.</Alert>
            ) : null}
            <Box>
              <Button variant="contained" color="secondary" onClick={handleGenerateProposal} disabled={proposalDisabled}>
                {proposalLoading ? "Generando..." : "Validar y generar propuesta"}
              </Button>
            </Box>
          </Box>
        ) : null}

        {proposal ? (
          <Box className="mb-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <Typography variant="h3">Propuesta calculada</Typography>
            <Box className="grid gap-3 md:grid-cols-4">
              <ProposalValue label="Total actual" value={proposal.total_actual === null ? "-" : formatCurrency(proposal.total_actual)} />
              <ProposalValue label="Total proyectado" value={proposal.total_proyectado === null ? "-" : formatCurrency(proposal.total_proyectado)} />
              <ProposalValue label="Diferencia estimada" value={proposal.diferencia_estimada === null ? "-" : formatCurrency(proposal.diferencia_estimada)} />
              <ProposalValue label="Decisión" value={DECISION_LABELS[proposal.decision] || proposal.decision} />
            </Box>
            <Typography variant="body2" color="text.secondary">
              Confianza: {proposal.confiabilidad}
              {proposal.mape === null ? "" : ` / MAPE ${formatNumber(proposal.mape)}%`}. {proposal.justificacion}
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={1}>
              <Chip label={`Fuente: ${proposal.fuente_decision || "backend_deterministico"}`} size="small" variant="outlined" sx={{ fontWeight: 800 }} />
              <Chip label={`Redacción: ${proposal.propuesta_generada_por || "llm_validado"}`} size="small" variant="outlined" sx={{ fontWeight: 800 }} />
            </Stack>
            {proposal.advertencias?.length ? <Alert severity="warning">{proposal.advertencias.join(" ")}</Alert> : null}
          </Box>
        ) : null}

        <Box component="form" onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <TextField
            fullWidth
            size="small"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            label="Pregunta"
            placeholder="Ej.: Necesito comprar 500 kg de cemento en 6 meses, ¿qué conviene?"
            inputProps={{ maxLength: 1000 }}
            disabled={loading}
          />
          <Button type="submit" variant="contained" disabled={!question.trim() || loading}>
            Enviar
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

function ProposalValue({ label, value }) {
  return (
    <Box className="rounded-lg border border-slate-200 bg-white p-3">
      <Typography variant="body2" color="text.secondary" fontWeight={800}>
        {label}
      </Typography>
      <Typography mt={0.5} fontWeight={800}>
        {value ?? "-"}
      </Typography>
    </Box>
  );
}
