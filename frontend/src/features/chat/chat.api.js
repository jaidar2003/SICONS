import { apiPost } from "../../shared/api/http.js";
import { apiGet, apiPatch } from "../../shared/api/http.js";

export function askChatQuestion(payload, token) {
  return apiPost("/chat/consultas", payload, token);
}

export function fetchChatConversations(token) {
  return apiGet("/chat/conversaciones", token);
}

export function createChatConversation(payload, token) {
  return apiPost("/chat/conversaciones", payload, token);
}

export function fetchChatConversationMessages(conversationId, token, options = {}) {
  const params = new URLSearchParams();
  if (options.limit) params.set("limit", String(options.limit));
  if (options.offset) params.set("offset", String(options.offset));
  if (options.order) params.set("order", options.order);
  const query = params.toString();
  return apiGet(`/chat/conversaciones/${conversationId}/mensajes${query ? `?${query}` : ""}`, token);
}

export function fetchChatProviderStatus(token, options = {}) {
  return apiGet(`/chat/status${options.verificar ? "?verificar=true" : ""}`, token);
}

export function updateChatConversation(conversationId, payload, token) {
  return apiPatch(`/chat/conversaciones/${conversationId}`, payload, token);
}

export function interpretCommercialNeed(payload, token) {
  return apiPost("/chat/presupuestacion/interpretar", payload, token);
}

export function generateCommercialProposal(payload, token) {
  return apiPost("/chat/presupuestacion/propuesta", payload, token);
}
