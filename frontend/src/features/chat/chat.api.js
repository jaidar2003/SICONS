import { apiPost } from "../../shared/api/http.js";

export function askChatQuestion(payload, token) {
  return apiPost("/chat/consultas", payload, token);
}

export function interpretCommercialNeed(payload, token) {
  return apiPost("/chat/presupuestacion/interpretar", payload, token);
}

export function generateCommercialProposal(payload, token) {
  return apiPost("/chat/presupuestacion/propuesta", payload, token);
}
