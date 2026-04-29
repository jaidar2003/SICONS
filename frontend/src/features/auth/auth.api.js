import { apiGet, apiPost } from "../../shared/api/http.js";

export function loginRequest(payload) {
  return apiPost("/auth/login", payload);
}

export function fetchCurrentUser(token) {
  return apiGet("/auth/me", token);
}

