const MODEL_LABELS = {
  prophet_base: "Prophet base",
  prophet_oficial_ipc_mayorista: "Prophet + oficial + IPC + mayorista",
  prophet_oficial_mayorista: "Prophet + oficial + mayorista",
  prophet_blue_ipc: "Prophet + blue + IPC",
  prophet_ipc: "Prophet + IPC",
  prophet_mayorista: "Prophet + mayorista",
  prophet_ipim_nivel_general: "Prophet + IPIM general",
  prophet_ipim_nivel_general_lags: "Prophet + IPIM + lags",
  prophet_ipim_nivel_general_medias_moviles: "Prophet + IPIM + medias móviles",
  prophet_ipim_nivel_general_variaciones: "Prophet + IPIM + variaciones",
  prophet_ipim_icc_var_materials: "Prophet + IPIM + ICC materiales",
  prophet_ipim_icc_var_general: "Prophet + IPIM + ICC general",
  prophet_ipim_cac_labour_force: "Prophet + IPIM + CAC mano de obra",
  prophet_ipim_cac_var_materials: "Prophet + IPIM + CAC materiales",
  prophet_ipim_cac_var_general: "Prophet + IPIM + CAC general",
  ensemble_simple_top2: "Ensemble simple (top 2)",
};

const REGRESSOR_LABELS = {
  ipim_nivel_general: "IPIM nivel general",
  icc_nivel_general: "ICC nivel general",
  icc_materials: "ICC materiales",
  icc_labour_force: "ICC mano de obra",
  icc_var_general: "ICC variación general",
  icc_var_materials: "ICC variación materiales",
  icc_var_labour: "ICC variación mano de obra",
  cac_general: "CAC general",
  cac_materials: "CAC materiales",
  cac_labour_force: "CAC mano de obra",
  cac_var_general: "CAC variación general",
  cac_var_materials: "CAC variación materiales",
  cac_var_labour: "CAC variación mano de obra",
  dolar_oficial: "Dólar oficial",
  dolar_mayorista: "Dólar mayorista",
  dolar_blue: "Dólar blue",
  ipc: "IPC",
};

function humanize(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function getModelDisplayName(modelId) {
  if (!modelId) return "Modelo no disponible";
  return MODEL_LABELS[modelId] || humanize(modelId);
}

export function getRegressorDisplayName(regressorId) {
  if (!regressorId) return "Sin regresor";
  return REGRESSOR_LABELS[regressorId] || humanize(regressorId);
}
