import { apiPost } from "../../shared/api/http.js";

export function askChatQuestion(payload, token) {
  return apiPost("/chat/consultas", payload, token);
}
