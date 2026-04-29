import { apiGet } from "../../shared/api/http.js";

export function fetchMateriales(token) {
  return apiGet("/materiales?activos=true", token);
}

export function fetchPresentaciones(token) {
  return apiGet("/presentaciones", token);
}

export function fetchFuentes(token) {
  return apiGet("/fuentes", token);
}

