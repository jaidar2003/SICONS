import { apiGet, apiPost } from "../../shared/api/http.js";

export function loginRequest(payload) {
  return apiPost("/auth/login", payload);
}

export function registerRequest(payload) {
  return apiPost("/auth/register", payload);
}

export function requestPasswordRecoveryRequest(payload) {
  return apiPost("/auth/password-recovery", payload);
}

export function requestPasswordResetRequest(payload) {
  return apiPost("/auth/password-reset", payload);
}

export function activateUserRequest(userId, token) {
  return apiPost(`/auth/usuarios/${userId}/habilitar`, {}, token);
}

export function fetchCurrentUser(token) {
  return apiGet("/auth/me", token);
}
