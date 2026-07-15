export function getMapePresentation(mape) {
  if (mape === null || mape === undefined || !Number.isFinite(Number(mape))) {
    return {
      label: "Error porcentual promedio (MAPE)",
      value: "Sin dato",
      explanation: "Este material no tiene una medición histórica de error disponible.",
    };
  }

  return {
    label: "Error porcentual promedio (MAPE)",
    value: `${new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(mape))}%`,
    explanation: "Cuanto menor es este valor, menor fue el error promedio en las evaluaciones históricas. No es una probabilidad de acierto ni garantiza resultados futuros.",
  };
}
