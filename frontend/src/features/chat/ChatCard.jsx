import AutoGraphIconModule from "@mui/icons-material/AutoGraph";
import ContentCopyIconModule from "@mui/icons-material/ContentCopy";
import DownloadIconModule from "@mui/icons-material/Download";
import ExpandMoreIconModule from "@mui/icons-material/ExpandMore";
import OpenInNewIconModule from "@mui/icons-material/OpenInNew";
import TimelineOutlinedIconModule from "@mui/icons-material/TimelineOutlined";
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Card, CardContent, Chip, CircularProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { resolveMuiIcon } from "../../shared/components/resolveMuiIcon.js";
import { formatCurrency, formatNumber } from "../../shared/utils/formatters.js";
import { fetchForecast, fetchSerie } from "../pricing/pricing.api.js";
import { PriceChart } from "../pricing/PriceChart.jsx";
import { INSUFFICIENT_CHART_DATA_MESSAGE, shouldShowInsufficientChartDataMessage } from "./chatVisualizationState.js";
import {
  askChatQuestion,
  createChatConversation,
  fetchChatConversationMessages,
  fetchChatConversations,
  generateCommercialProposal,
  interpretCommercialNeed,
  updateChatConversation,
} from "./chat.api.js";

const AutoGraphIcon = resolveMuiIcon(AutoGraphIconModule);
const ContentCopyIcon = resolveMuiIcon(ContentCopyIconModule);
const DownloadIcon = resolveMuiIcon(DownloadIconModule);
const ExpandMoreIcon = resolveMuiIcon(ExpandMoreIconModule);
const OpenInNewIcon = resolveMuiIcon(OpenInNewIconModule);
const TimelineOutlinedIcon = resolveMuiIcon(TimelineOutlinedIconModule);
const PROVIDER_LABELS = {
  facultad: "UM",
  claude: "Claude",
};
const VISUALIZATION_LABELS = {
  PRICE_HISTORY: "Histórico de precios",
  FORECAST: "Forecast",
  PRICE_HISTORY_FORECAST: "Histórico + forecast",
};
const MATERIAL_RESOLUTION_LABELS = {
  pregunta: "Pregunta",
  contexto: "Conversación",
  seleccionado: "Selector",
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
const MESSAGE_PAGE_SIZE = 40;

function materialKey(nombre) {
  return String(nombre || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function normalizeText(text) {
  return String(text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function questionMentionsKnownMaterial(text, materiales) {
  const normalized = normalizeText(text);
  return materiales.some((material) => {
    const key = materialKey(material.nombre);
    const nameTokens = key.split("-").filter(Boolean);
    return nameTokens.some((token) => token.length >= 4 && normalized.includes(token));
  });
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

function mapStoredMessage(message) {
  if (message.role === "user") {
    return { role: "user", text: message.content };
  }
  return {
    role: "assistant",
    question: null,
    text: message.content,
    provider: message.proveedor_ia,
    providerUsed: Boolean(message.proveedor_ia),
    fallbackUsed: Boolean(message.fallback_usado),
    contextUsed: Boolean(message.contexto_usado),
    intent: message.tipo_intencion,
    sources: message.fuentes_recuperadas || [],
    sourceEvidence: message.fuentes_evidencia || [],
    resolvedMaterialId: message.material_resuelto_id || null,
    resolvedMaterial: message.material_resuelto,
    materialResolutionSource: message.material_resolution_source || null,
    resolvedHorizon: message.horizonte_resuelto,
    visualization: message.visualizacion_sugerida || null,
    rejected: message.tipo_intencion === "FUERA_ALCANCE",
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

function questionMentionsHorizon(text) {
  const normalized = normalizeText(text);
  return /\b\d{1,2}\s*mes(?:es)?\b/.test(normalized) || /\bhorizonte\b/.test(normalized) || /\ba\s*\d{1,2}\s*mes(?:es)?\b/.test(normalized);
}

export function ChatCard({ token, selectedMaterial, forecastHorizon, isAdmin, materiales = [], showPrices = true, onOpenVisualization }) {
  const commercialMaterials = useMemo(
    () => materiales.filter((material) => SUPPORTED_PRODUCT_KEYS.has(materialKey(material.nombre))),
    [materiales]
  );
  const draftStorageKey = `${COMMERCIAL_DRAFT_STORAGE_KEY}.${selectedMaterial?.id ?? "none"}`;
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([initialMessage(isAdmin)]);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [messageOffset, setMessageOffset] = useState(0);
  const [hasOlderMessages, setHasOlderMessages] = useState(false);
  const [conversationTitleDraft, setConversationTitleDraft] = useState("");
  const [renamingConversation, setRenamingConversation] = useState(false);
  const [draft, setDraft] = useState(createEmptyDraft);
  const [interpretation, setInterpretation] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [commercialFlowReady, setCommercialFlowReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastResolvedMaterialId, setLastResolvedMaterialId] = useState(null);
  const draftQuantity = Number(draft.quantity);
  const proposalDisabled =
    proposalLoading ||
    !commercialMaterials.length ||
    !draft.materialId ||
    !Number.isFinite(draftQuantity) ||
    draftQuantity <= 0 ||
    (!draft.targetDate && (!Number(draft.horizon) || Number(draft.horizon) < 1 || Number(draft.horizon) > 12));
  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) || null,
    [activeConversationId, conversations]
  );
  const messagePage = Math.floor(messageOffset / MESSAGE_PAGE_SIZE) + 1;

  async function loadConversations() {
    if (!token) return;
    const result = await fetchChatConversations(token);
    setConversations(result);
    if (!activeConversationId && result.length) {
      setActiveConversationId(result[0].id);
    }
  }

  async function loadConversationMessages(conversationId, offset = 0) {
    if (!conversationId || !token) {
      setMessages([initialMessage(isAdmin)]);
      setHasOlderMessages(false);
      return;
    }
    setConversationLoading(true);
    try {
      const storedMessages = await fetchChatConversationMessages(conversationId, token, {
        limit: MESSAGE_PAGE_SIZE + 1,
        offset,
        order: "desc",
      });
      const visibleMessages = storedMessages.slice(0, MESSAGE_PAGE_SIZE).reverse();
      setHasOlderMessages(storedMessages.length > MESSAGE_PAGE_SIZE);
      setMessages(visibleMessages.length ? visibleMessages.map(mapStoredMessage) : [initialMessage(isAdmin)]);
      const lastAssistant = storedMessages.find((message) => message.role === "assistant" && message.material_resuelto_id);
      if (lastAssistant?.material_resuelto_id) setLastResolvedMaterialId(lastAssistant.material_resuelto_id);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setConversationLoading(false);
    }
  }

  async function handleNewConversation() {
    setError("");
    try {
      const created = await createChatConversation({ titulo: "Nueva conversación" }, token);
      setConversations((current) => [created, ...current]);
      setActiveConversationId(created.id);
      setMessageOffset(0);
      setHasOlderMessages(false);
      setMessages([initialMessage(isAdmin)]);
      setLastResolvedMaterialId(null);
    } catch (newError) {
      setError(newError.message);
    }
  }

  async function handleArchiveConversation() {
    if (!activeConversationId) return;
    setError("");
    try {
      await updateChatConversation(activeConversationId, { archived: true }, token);
      const remaining = conversations.filter((conversation) => conversation.id !== activeConversationId);
      setConversations(remaining);
      setActiveConversationId(remaining[0]?.id || null);
      setMessageOffset(0);
      setHasOlderMessages(false);
      if (!remaining.length) setMessages([initialMessage(isAdmin)]);
    } catch (archiveError) {
      setError(archiveError.message);
    }
  }

  async function handleRenameConversation() {
    if (!activeConversationId) return;
    const title = conversationTitleDraft.trim();
    if (!title) {
      setError("El título de la conversación no puede quedar vacío.");
      return;
    }
    setError("");
    setRenamingConversation(true);
    try {
      const updated = await updateChatConversation(activeConversationId, { titulo: title }, token);
      setConversations((current) =>
        current.map((conversation) => (conversation.id === updated.id ? updated : conversation))
      );
      setConversationTitleDraft(updated.titulo);
    } catch (renameError) {
      setError(renameError.message);
    } finally {
      setRenamingConversation(false);
    }
  }

  function handleSelectConversation(conversationId) {
    setMessageOffset(0);
    setActiveConversationId(conversationId);
  }

  function handleOlderMessagesPage() {
    if (hasOlderMessages) setMessageOffset((current) => current + MESSAGE_PAGE_SIZE);
  }

  function handleRecentMessagesPage() {
    setMessageOffset((current) => Math.max(0, current - MESSAGE_PAGE_SIZE));
  }

  useEffect(() => {
    loadConversations().catch((loadError) => setError(loadError.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    loadConversationMessages(activeConversationId, messageOffset).catch((loadError) => setError(loadError.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConversationId, messageOffset]);

  useEffect(() => {
    setConversationTitleDraft(activeConversation?.titulo || "");
  }, [activeConversation?.id, activeConversation?.titulo]);

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
            providerUsed: Boolean(result.proveedor_utilizado),
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
      const materialIdForQuestion = questionMentionsKnownMaterial(trimmed, materiales)
        ? null
        : lastResolvedMaterialId || selectedMaterial?.id || null;
      let conversationId = activeConversationId;
      let createdConversation = null;
      if (!conversationId) {
        createdConversation = await createChatConversation({ titulo: trimmed }, token);
        conversationId = createdConversation.id;
      }
      const shouldSendHorizon = !activeConversationId || questionMentionsHorizon(trimmed);
      const result = await askChatQuestion(
        {
          pregunta: trimmed,
          material_id: materialIdForQuestion,
          conversation_id: conversationId,
          ...(shouldSendHorizon ? { horizonte_meses: forecastHorizon } : {}),
          historial,
        },
        token
      );
      if (result.material_resuelto_id) {
        setLastResolvedMaterialId(result.material_resuelto_id);
      }
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          question: trimmed,
          text: result.respuesta,
          provider: result.proveedor_ia,
          providerUsed: Boolean(result.proveedor_utilizado),
          fallbackUsed: Boolean(result.fallback_usado),
          contextUsed: Boolean(result.contexto_usado),
          intent: result.tipo_intencion,
          sources: result.fuentes_recuperadas || [],
          sourceEvidence: result.fuentes_evidencia || [],
          resolvedMaterialId: result.material_resuelto_id || null,
          resolvedMaterial: result.material_resuelto,
          materialResolutionSource: result.material_resolution_source || null,
          resolvedHorizon: result.horizonte_resuelto,
          visualization: result.visualizacion_sugerida || null,
          rejected: !result.aceptada,
        },
      ]);
      window.dispatchEvent(new Event("buildwise:chat-config-updated"));
      if (createdConversation) {
        setConversations((current) => [createdConversation, ...current]);
        setActiveConversationId(createdConversation.id);
        setMessageOffset(0);
        setHasOlderMessages(false);
      }
      loadConversations().catch(() => {});
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
      window.dispatchEvent(new Event("buildwise:chat-config-updated"));
      setProposal(result);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: result.propuesta,
          provider: result.proveedor_ia,
          providerUsed: Boolean(result.proveedor_utilizado),
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

        <Box className="mb-3 grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-center">
          <TextField
            select
            size="small"
            label="Conversación"
            value={activeConversationId || ""}
            onChange={(event) => handleSelectConversation(event.target.value ? Number(event.target.value) : null)}
          >
            {!conversations.length ? <MenuItem value="">Sin conversaciones guardadas</MenuItem> : null}
            {conversations.map((conversation) => (
              <MenuItem key={conversation.id} value={conversation.id}>
                {conversation.titulo}
              </MenuItem>
            ))}
          </TextField>
          <Button variant="outlined" onClick={handleNewConversation}>
            Nueva conversación
          </Button>
          <Button variant="outlined" color="secondary" onClick={handleArchiveConversation} disabled={!activeConversationId}>
            Archivar
          </Button>
          <TextField
            size="small"
            label="Título"
            value={conversationTitleDraft}
            disabled={!activeConversationId}
            onChange={(event) => setConversationTitleDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleRenameConversation();
              }
            }}
            className="md:col-span-2"
          />
          <Button
            variant="outlined"
            onClick={handleRenameConversation}
            disabled={!activeConversationId || renamingConversation || conversationTitleDraft.trim() === activeConversation?.titulo}
          >
            {renamingConversation ? "Guardando..." : "Guardar título"}
          </Button>
        </Box>

        {error ? <Alert severity="error" className="mb-3">{error}</Alert> : null}

        <Box className="mb-4 flex min-h-[300px] flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <Box className="flex flex-wrap items-center justify-between gap-2">
            <Typography variant="caption" color="text.secondary">
              Página {messagePage} · {MESSAGE_PAGE_SIZE} mensajes por página
            </Typography>
            <Stack direction="row" spacing={1}>
              <Button size="small" variant="outlined" onClick={handleRecentMessagesPage} disabled={messageOffset === 0 || conversationLoading}>
                Más recientes
              </Button>
              <Button size="small" variant="outlined" onClick={handleOlderMessagesPage} disabled={!hasOlderMessages || conversationLoading}>
                Anteriores
              </Button>
            </Stack>
          </Box>
          {messages.map((message, index) => (
            <Box
              key={`${message.role}-${index}`}
              className={`${message.visualization ? "max-w-full" : "max-w-[85%]"} rounded-xl px-4 py-3 ${message.role === "user" ? "ml-auto bg-teal-700 text-white" : "bg-white text-slate-800 shadow-sm"}`}
            >
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {message.text}
              </Typography>
              {message.role === "assistant" && !message.rejected ? (
                <Box className="mt-2 flex flex-wrap gap-1.5">
                  <Chip label={message.providerUsed ? `IA usada: ${PROVIDER_LABELS[message.provider] || message.provider || "desconocida"}` : "Sin IA"} size="small" variant="outlined" sx={{ fontWeight: 800 }} />
                  {message.fallbackUsed ? <Chip label="Fallback activado" size="small" color="warning" sx={{ fontWeight: 800 }} /> : null}
                  {message.intent ? <Chip label={`Intención: ${message.intent}`} size="small" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {message.contextUsed ? <Chip label="RAG backend" size="small" color="success" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {message.resolvedMaterial ? <Chip label={`Material: ${message.resolvedMaterial}`} size="small" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {message.intent !== "HISTORICO" && message.resolvedHorizon ? <Chip label={`Horizonte: ${message.resolvedHorizon} meses`} size="small" variant="outlined" sx={{ fontWeight: 800 }} /> : null}
                  {(message.sources || []).map((source) => (
                    <Chip key={source} label={source} size="small" variant="outlined" sx={{ fontWeight: 800 }} />
                  ))}
                </Box>
              ) : null}
              {message.role === "assistant" && !message.rejected && (message.contextUsed || message.visualization) ? (
                <RagEvidencePanel message={message} />
              ) : null}
              {message.role === "assistant" && !message.rejected ? <ChatMessageActions message={message} /> : null}
              {message.visualization ? (
                <ChatVisualization
                  visualization={message.visualization}
                  token={token}
                  materiales={materiales}
                  selectedMaterial={selectedMaterial}
                  showPrices={showPrices}
                  onOpenVisualization={onOpenVisualization}
                />
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
          {conversationLoading ? (
            <Box className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-slate-600 shadow-sm">
              <CircularProgress size={16} />
              <Typography variant="body2">Cargando conversación...</Typography>
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

function RagEvidencePanel({ message }) {
  const rows = [
    ["Intención", message.intent || "-"],
    ["Material", message.resolvedMaterial || "-"],
    ["Resolución material", MATERIAL_RESOLUTION_LABELS[message.materialResolutionSource] || message.materialResolutionSource || "-"],
    ...(message.intent === "HISTORICO" ? [] : [["Horizonte", message.resolvedHorizon ? `${message.resolvedHorizon} meses` : "-"]]),
    ["Fuentes", message.sources?.length ? message.sources.join(", ") : "-"],
    ["Visualización", message.visualization ? VISUALIZATION_LABELS[message.visualization.tipo] || message.visualization.tipo : "-"],
  ];
  const summary = [
    message.intent ? `Intención: ${message.intent}` : null,
    message.resolvedMaterial ? `Material: ${message.resolvedMaterial}` : null,
    message.resolvedHorizon ? `Horizonte: ${message.resolvedHorizon} meses` : null,
    message.sources?.length ? `Fuentes: ${message.sources.length}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Accordion className="mt-3 rounded-lg border border-slate-200 bg-slate-50" disableGutters elevation={0} defaultExpanded={false}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box className="min-w-0">
          <Typography variant="body2" fontWeight={900} color="text.secondary">
            Datos usados por el RAG
          </Typography>
          <Typography variant="body2" color="text.secondary" noWrap title={summary || "Sin detalle disponible"}>
            {summary || "Resumen corto disponible al expandir"}
          </Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Box className="grid gap-2 md:grid-cols-2">
          {rows.map(([label, value]) => (
            <Box key={label} className="rounded-md bg-white px-3 py-2">
              <Typography variant="caption" color="text.secondary" fontWeight={800}>
                {label}
              </Typography>
              <Typography variant="body2" fontWeight={800}>
                {value}
              </Typography>
            </Box>
          ))}
        </Box>
        {message.sourceEvidence?.length ? <SourceEvidenceList evidence={message.sourceEvidence} /> : null}
      </AccordionDetails>
    </Accordion>
  );
}

function SourceEvidenceList({ evidence }) {
  return (
    <Box className="mt-3 grid gap-2">
      {evidence.map((sourceEvidence) => (
        <Accordion key={sourceEvidence.source} disableGutters elevation={0} className="border border-slate-200">
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2" fontWeight={900}>
              Fuente expandible: {sourceEvidence.source}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {sourceEvidence.records?.length ? (
              <Box className="grid gap-2">
                {sourceEvidence.records.map((record, index) => (
                  <Box key={`${sourceEvidence.source}-${record.fecha || index}`} className="rounded-md bg-white p-3">
                    <Typography variant="body2" fontWeight={900}>
                      {record.fecha || "Sin fecha"}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Precio: {record.precio_normalizado ? `ARS ${record.precio_normalizado}` : "-"} {record.unidad_base ? `por ${record.unidad_base}` : ""}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Fuente: {record.fuente || "-"}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Comprobante: {record.comprobante || "-"}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                La fuente fue usada, pero no hay registros detallados para mostrar.
              </Typography>
            )}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}

function buildEvidencePayload(message) {
  return {
    pregunta: message.question || null,
    respuesta: message.text,
    tipo_intencion: message.intent || null,
    contexto_usado: Boolean(message.contextUsed),
    fuentes_recuperadas: message.sources || [],
    fuentes_evidencia: message.sourceEvidence || [],
    material_resuelto_id: message.resolvedMaterialId || null,
    material_resuelto: message.resolvedMaterial || null,
    material_resolution_source: message.materialResolutionSource || null,
    horizonte_resuelto: message.intent === "HISTORICO" ? null : message.resolvedHorizon || null,
    proveedor_utilizado: Boolean(message.providerUsed),
    proveedor_ia: message.provider || null,
    fallback_usado: Boolean(message.fallbackUsed),
    visualizacion_sugerida: message.visualization || null,
  };
}

function buildSummaryText(message) {
  const payload = buildEvidencePayload(message);
  return [
    `Pregunta: ${payload.pregunta || "-"}`,
    `Respuesta: ${payload.respuesta || "-"}`,
    `Intención: ${payload.tipo_intencion || "-"}`,
    `Material: ${payload.material_resuelto || "-"}`,
    ...(payload.tipo_intencion === "HISTORICO" ? [] : [`Horizonte: ${payload.horizonte_resuelto ? `${payload.horizonte_resuelto} meses` : "-"}`]),
    `Fuentes: ${payload.fuentes_recuperadas.length ? payload.fuentes_recuperadas.join(", ") : "-"}`,
    `Visualización: ${payload.visualizacion_sugerida ? VISUALIZATION_LABELS[payload.visualizacion_sugerida.tipo] || payload.visualizacion_sugerida.tipo : "-"}`,
  ].join("\n");
}

function ChatMessageActions({ message }) {
  async function copySummary() {
    const text = buildSummaryText(message);
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    }
  }

  function downloadEvidence() {
    const blob = new Blob([JSON.stringify(buildEvidencePayload(message), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `buildwise-rag-evidencia-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Box className="mt-3 grid gap-2">
      <Box className="flex flex-wrap gap-2">
        <Button size="small" variant="outlined" startIcon={<ContentCopyIcon fontSize="small" />} onClick={copySummary}>
          Copiar resumen
        </Button>
        <Button size="small" variant="outlined" startIcon={<DownloadIcon fontSize="small" />} onClick={downloadEvidence}>
          Descargar evidencia
        </Button>
      </Box>
      <Accordion disableGutters elevation={0} className="border border-slate-200">
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="body2" fontWeight={900}>
            Modo auditoría/demo
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box className="grid gap-2 md:grid-cols-2">
            {Object.entries(buildEvidencePayload(message)).map(([key, value]) => (
              <Box key={key} className="rounded-md bg-slate-50 p-2">
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  {key}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                  {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value ?? "-")}
                </Typography>
              </Box>
            ))}
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
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

function ChatVisualization({ visualization, token, materiales, selectedMaterial, showPrices, onOpenVisualization }) {
  const [serie, setSerie] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [loadingChart, setLoadingChart] = useState(false);
  const [chartError, setChartError] = useState("");
  const materialId = visualization?.material_id;
  const horizonteMeses = visualization?.horizonte_meses || 3;
  const material = useMemo(
    () => materiales.find((item) => Number(item.id) === Number(materialId)) || (Number(selectedMaterial?.id) === Number(materialId) ? selectedMaterial : null),
    [materiales, materialId, selectedMaterial]
  );
  const isForecastChart = visualization?.tipo === "FORECAST" || visualization?.tipo === "PRICE_HISTORY_FORECAST";
  const shouldShowInsufficientData = shouldShowInsufficientChartDataMessage({
    loading: loadingChart,
    error: chartError,
    serie,
    forecast,
  });

  useEffect(() => {
    let active = true;
    async function loadChartData() {
      if (!materialId) return;
      setLoadingChart(true);
      setChartError("");
      try {
        const [serieResult, forecastResult] = await Promise.all([
          fetchSerie({ materialId, token }),
          visualization.tipo === "PRICE_HISTORY" ? Promise.resolve(null) : fetchForecast({ materialId, horizonteMeses, token }),
        ]);
        if (!active) return;
        setSerie(serieResult || []);
        setForecast(forecastResult);
      } catch (error) {
        if (active) setChartError(error.message);
      } finally {
        if (active) setLoadingChart(false);
      }
    }
    loadChartData();
    return () => {
      active = false;
    };
  }, [materialId, horizonteMeses, token, visualization.tipo]);

  if (!visualization || !materialId) return null;

  return (
    <Box className="mt-3 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
      <Box className="flex flex-col gap-2 border-b border-slate-200 bg-white px-3 py-2 md:flex-row md:items-center md:justify-between">
        <Box>
          <Typography variant="body2" fontWeight={900}>
            {VISUALIZATION_LABELS[visualization.tipo] || "Visualización"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            El gráfico usa endpoints de BuildWise, no datos generados por el modelo.
          </Typography>
        </Box>
        {onOpenVisualization ? (
          <Button
            size="small"
            variant="outlined"
            startIcon={isForecastChart ? <TimelineOutlinedIcon fontSize="small" /> : <AutoGraphIcon fontSize="small" />}
            endIcon={<OpenInNewIcon fontSize="small" />}
            onClick={() => onOpenVisualization(visualization)}
          >
            Abrir vista
          </Button>
        ) : null}
      </Box>
      {chartError ? <Alert severity="warning">No fue posible cargar el gráfico solicitado: {chartError}</Alert> : null}
      {loadingChart ? (
        <Box className="flex items-center gap-2 p-3 text-slate-600">
          <CircularProgress size={16} />
          <Typography variant="body2">Cargando gráfico...</Typography>
        </Box>
      ) : shouldShowInsufficientData ? (
        <Alert severity="info">{INSUFFICIENT_CHART_DATA_MESSAGE}</Alert>
      ) : (
        <PriceChart
          serie={serie}
          forecast={visualization.tipo === "PRICE_HISTORY" ? null : forecast}
          selectedMaterial={material}
          showPrices={showPrices}
          className="m-0 border-0 shadow-none"
        />
      )}
    </Box>
  );
}
