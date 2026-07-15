export const VISUALIZATION_LABELS = {
  PRICE_HISTORY: "Histórico de precios",
  FORECAST: "Proyección",
  PRICE_HISTORY_FORECAST: "Histórico + proyección",
};

const PROVIDER_LABELS = { facultad: "UM", claude: "Claude" };
const MATERIAL_RESOLUTION_LABELS = { pregunta: "la consulta", contexto: "la conversación", seleccionado: "el selector" };
const INTENT_LABELS = {
  HISTORICO: "Consultar precios históricos",
  FORECAST: "Consultar una proyección",
  RECOMENDACION: "Evaluar una compra",
  PRESUPUESTO: "Preparar un presupuesto",
  CATALOGO: "Consultar materiales",
  ADMIN: "Realizar una tarea administrativa",
  FUERA_ALCANCE: "Consulta fuera del alcance",
};

export function getMessageDetailPresentation(message) {
  const rows = [
    ["Qué entendió", INTENT_LABELS[message.intent] || message.intent || "Consulta general"],
    ["Material", message.resolvedMaterial || "-"],
    ["Material indicado en", MATERIAL_RESOLUTION_LABELS[message.materialResolutionSource] || message.materialResolutionSource || "-"],
    ...(message.intent === "HISTORICO" ? [] : [["Horizonte", message.resolvedHorizon ? `${message.resolvedHorizon} meses` : "-"]]),
    ["Fuentes", message.sources?.length ? message.sources.join(", ") : "-"],
    ["Visualización", message.visualization ? VISUALIZATION_LABELS[message.visualization.tipo] || message.visualization.tipo : "-"],
    ["Cálculos", message.contextUsed ? "Realizados por BuildWise" : "No se necesitaron cálculos"],
    ["Redacción", message.providerUsed ? `Asistente ${PROVIDER_LABELS[message.provider] || message.provider || "configurado"}` : "Respuesta directa de BuildWise"],
  ];
  const summary = [
    message.resolvedMaterial ? `Material: ${message.resolvedMaterial}` : null,
    message.resolvedHorizon ? `Horizonte: ${message.resolvedHorizon} meses` : null,
    message.sources?.length ? `${message.sources.length} ${message.sources.length === 1 ? "fuente" : "fuentes"}` : null,
  ].filter(Boolean).join(" · ");

  return { rows, summary };
}
