export function normalizeMaterialName(name) {
  return String(name || "")
    .trim()
    .toLowerCase();
}

export function isCementMaterial(name) {
  return normalizeMaterialName(name) === "cemento portland";
}

export function isPastinaMaterial(name) {
  return normalizeMaterialName(name).includes("pastina");
}

export function isMembranaMaterial(name) {
  return normalizeMaterialName(name) === "membrana megaflex";
}

export function getMaterialPresentation(name, unitBase = "unidad") {
  if (isCementMaterial(name)) {
    return {
      type: "cement",
      displayMultiplier: 1,
      displayUnitLabel: unitBase,
      primaryPriceLabel: "Precio normalizado",
      primaryPriceHelper: "Base comparable por cambio de packaging",
      tablePriceLabel: "Precio/kg",
      chartAxisLabel: "ARS/kg",
      tooltipPriceLabel: "Precio/kg",
      summaryUnitText: `por ${unitBase}`,
      fixedPresentationLabel: null,
    };
  }

  if (isPastinaMaterial(name)) {
    return {
      type: "fixed",
      displayMultiplier: 1,
      displayUnitLabel: "envase 1 kg",
      primaryPriceLabel: "Precio comercial",
      primaryPriceHelper: "Presentacion fija de 1 kg",
      tablePriceLabel: "Precio 1 kg",
      chartAxisLabel: "ARS por envase 1 kg",
      tooltipPriceLabel: "Precio 1 kg",
      summaryUnitText: "por envase de 1 kg",
      fixedPresentationLabel: "1 kg",
    };
  }

  if (isMembranaMaterial(name)) {
    return {
      type: "fixed",
      displayMultiplier: 20,
      displayUnitLabel: "balde 20 kg",
      primaryPriceLabel: "Precio comercial",
      primaryPriceHelper: "Presentacion fija de 20 kg",
      tablePriceLabel: "Precio 20 kg",
      chartAxisLabel: "ARS por balde 20 kg",
      tooltipPriceLabel: "Precio 20 kg",
      summaryUnitText: "por balde de 20 kg",
      fixedPresentationLabel: "20 kg",
    };
  }

  return {
    type: "generic",
    displayMultiplier: 1,
    displayUnitLabel: unitBase,
    primaryPriceLabel: "Precio de referencia",
    primaryPriceHelper: `Base mostrada por ${unitBase}`,
    tablePriceLabel: `Precio/${unitBase}`,
    chartAxisLabel: `ARS/${unitBase}`,
    tooltipPriceLabel: `Precio/${unitBase}`,
    summaryUnitText: `por ${unitBase}`,
    fixedPresentationLabel: null,
  };
}

export function getDisplayPrice(value, materialName, unitBase = "unidad") {
  const presentation = getMaterialPresentation(materialName, unitBase);
  return Number(value) * presentation.displayMultiplier;
}
