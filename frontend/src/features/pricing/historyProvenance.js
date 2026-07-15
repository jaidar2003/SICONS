export function getDataOriginPresentation(point) {
  if (point?.origen_dato === "REAL") {
    return { label: "Real observado", color: "success" };
  }
  if (point?.origen_dato === "ESTIMADO") {
    return { label: "Estimado", color: "warning" };
  }
  return { label: "Sin clasificar", color: "default" };
}

export function getPurchasedPresentationLabel(point) {
  if (point?.presentacion_nombre) return point.presentacion_nombre;
  if (point?.presentacion_cantidad_base && point?.presentacion_unidad) {
    return `${point.presentacion_cantidad_base} ${point.presentacion_unidad}`;
  }
  return point?.origen_dato === "ESTIMADO" ? "No aplica" : "Sin dato";
}

export function getNormalizedPriceLabel(unit) {
  return `Precio normalizado (ARS/${unit || "unidad"})`;
}
