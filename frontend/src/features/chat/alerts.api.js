import { apiGet, apiPatch } from "../../shared/api/http.js";

export function listAlerts(params = {}, token) {
  const query = new URLSearchParams();
  if (params.solo_no_leidas) query.append("solo_no_leidas", "true");
  if (params.material_id) query.append("material_id", params.material_id);
  
  return apiGet(`/alertas?${query.toString()}`, token);
}

export function markAlertsAsRead(alertaIds, token) {
  return apiPatch("/alertas/lectura", { alerta_ids: alertaIds, leida: true }, token);
}
