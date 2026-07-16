const DEFAULT_SUGGESTIONS = [
  "¿Cuál es el último precio?",
  "¿Qué materiales hay?",
  "¿Cómo hago un presupuesto?",
];

const SUGGESTIONS_BY_INTENT = {
  CATALOGO: ["¿Cuál es el último precio?", "Mostrame el histórico", "¿Cómo hago un presupuesto?"],
  HISTORICO: ["¿Cuánto aumentó?", "Mostrame la proyección a 3 meses", "Explicámelo más fácil"],
  FORECAST: ["¿Y a 6 meses?", "¿Qué significa el MAPE?", "¿Me conviene comprar?"],
  RECOMENDACION: ["Explicámelo más fácil", "¿Qué datos usaste?", "Quiero analizar una cantidad"],
  PRESUPUESTO: ["¿Me alcanza?", "¿Conviene comprar por etapas?", "Quiero cambiar la cantidad"],
};

export function getFollowUpSuggestions(message) {
  if (!message || message.rejected) return [];
  if (Array.isArray(message.suggestions) && message.suggestions.length) return message.suggestions.slice(0, 4);
  return SUGGESTIONS_BY_INTENT[message.intent] || DEFAULT_SUGGESTIONS;
}

export function formatUnderstanding(understanding) {
  if (!understanding) return "";
  const parts = [];
  if (understanding.material) parts.push(understanding.material);
  if (understanding.quantity != null) {
    const unit = understanding.input_unit === "bag" ? "bolsas" : understanding.input_unit || "unidades";
    parts.push(`${understanding.quantity} ${unit}`);
  }
  if (understanding.budget != null) parts.push(`presupuesto $${understanding.budget}`);
  if (understanding.horizon_months != null) parts.push(`${understanding.horizon_months} meses`);
  return parts.join(" · ");
}

export function splitProgressiveAnswer(text) {
  const paragraphs = String(text || "").split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
  return {
    result: paragraphs[0] || "",
    explanation: paragraphs.slice(1),
  };
}

export function updateCommercialDraftContext(current, field, value) {
  if (field === "materialId" && String(current.materialId) !== String(value)) {
    return { ...current, materialId: String(value), quantity: "", budget: "", request: "" };
  }
  return { ...current, [field]: value };
}

export function getRecoverableChatError(error) {
  if (error?.name === "AbortError") return "Consulta detenida. Podés modificarla o intentarlo nuevamente.";
  const message = String(error?.message || error || "").toLowerCase();
  if (message.includes("401")) return "Tu sesión venció. Volvé a iniciar sesión para continuar.";
  if (message.includes("403")) return "No tenés permiso para realizar esa consulta.";
  if (message.includes("503") || message.includes("timeout") || message.includes("network") || message.includes("fetch")) {
    return "BuildWise no está disponible temporalmente. Tu consulta no se perdió y podés reintentar.";
  }
  return "No pude completar la consulta. Revisá los datos o intentá nuevamente.";
}

export function getMissingDataPrompt(missingFields = [], materialNames = []) {
  const missing = new Set(missingFields);
  if (missing.has("producto")) {
    const options = materialNames.length ? ` Opciones: ${materialNames.join(", ")}.` : "";
    return `¿Que material necesitas?${options}`;
  }
  if (missing.has("cantidad")) return "¿Que cantidad necesitas? Podes indicarla en bolsas, kilogramos u otra unidad disponible.";
  if (missing.has("fase_obra")) return "¿Para que etapa de la obra es la compra: estructura, terminaciones o impermeabilizacion?";
  if (missing.has("fecha_objetivo_uso_o_horizonte_meses")) return "¿Para cuando necesitas el material o cuantos meses queres analizar?";
  return "Entendi la necesidad. Revisa los datos y confirma para que BuildWise calcule la propuesta.";
}
