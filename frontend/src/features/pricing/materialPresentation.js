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
      displayMultiplier: 25,
      displayUnitLabel: "bolsa 25 kg",
      primaryPriceLabel: "Bolsa 25 kg",
      primaryPriceHelper: "Presentacion comercial actual",
      tablePriceLabel: "Bolsa 25 kg",
      chartAxisLabel: "ARS por bolsa 25 kg",
      tooltipPriceLabel: "Bolsa 25 kg",
      summaryUnitText: "por bolsa de 25 kg",
      fixedPresentationLabel: "Bolsa 25 kg",
    };
  }

  if (isPastinaMaterial(name)) {
    return {
      type: "fixed",
      displayMultiplier: 1,
      displayUnitLabel: "caja 1 kg",
      primaryPriceLabel: "Caja 1 kg",
      primaryPriceHelper: "Presentacion comercial de 1 kg",
      tablePriceLabel: "Caja 1 kg",
      chartAxisLabel: "ARS por caja 1 kg",
      tooltipPriceLabel: "Caja 1 kg",
      summaryUnitText: "por caja de 1 kg",
      fixedPresentationLabel: "Caja 1 kg",
    };
  }

  if (isMembranaMaterial(name)) {
    return {
      type: "fixed",
      displayMultiplier: 20,
      displayUnitLabel: "balde 20 kg",
      primaryPriceLabel: "Balde 20 kg",
      primaryPriceHelper: "Presentacion fija de 20 kg",
      tablePriceLabel: "Balde 20 kg",
      chartAxisLabel: "ARS por balde 20 kg",
      tooltipPriceLabel: "Balde 20 kg",
      summaryUnitText: "por balde de 20 kg",
      fixedPresentationLabel: "Balde 20 kg",
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
