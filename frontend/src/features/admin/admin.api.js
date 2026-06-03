import { apiDelete, apiGet, apiPatch, apiPost } from "../../shared/api/http.js";

export function fetchCommercialMargins(token) {
  return apiGet("/admin/margenes", token);
}

export function createCommercialMargin(payload, token) {
  return apiPost("/admin/margenes", payload, token);
}

export function updateCommercialMargin(marginId, payload, token) {
  return apiPatch(`/admin/margenes/${marginId}`, payload, token);
}

export function fetchUsers(token) {
  return apiGet("/auth/usuarios", token);
}

export function activateUser(userId, token) {
  return apiPost(`/auth/usuarios/${userId}/habilitar`, {}, token);
}

export function deleteUser(userId, token) {
  return apiDelete(`/auth/usuarios/${userId}`, token);
}

export function fetchChatConfig(token) {
  return apiGet("/chat/config", token);
}

export function updateChatConfig(payload, token) {
  return apiPatch("/chat/config", payload, token);
}
