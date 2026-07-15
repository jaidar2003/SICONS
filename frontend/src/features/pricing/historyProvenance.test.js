import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { getDataOriginPresentation, getNormalizedPriceLabel, getPurchasedPresentationLabel } from "./historyProvenance.js";

describe("historical price provenance", () => {
  it("identifies observed and estimated records without treating forecasts as history", () => {
    assert.deepEqual(getDataOriginPresentation({ origen_dato: "REAL" }), { label: "Real observado", color: "success" });
    assert.deepEqual(getDataOriginPresentation({ origen_dato: "ESTIMADO" }), { label: "Estimado", color: "warning" });
    assert.equal(getDataOriginPresentation({}).label, "Sin clasificar");
  });

  it("shows the presentation actually purchased instead of a calculated equivalent", () => {
    const historicalBag = {
      presentacion_nombre: "Bolsa 50 kg",
      precio_equivalente_25kg: "4500.00",
    };

    assert.equal(getPurchasedPresentationLabel(historicalBag), "Bolsa 50 kg");
  });

  it("keeps the normalized comparison unit explicit", () => {
    assert.equal(getNormalizedPriceLabel("kg"), "Precio normalizado (ARS/kg)");
    assert.equal(getNormalizedPriceLabel(null), "Precio normalizado (ARS/unidad)");
  });

  it("does not invent a purchased presentation for estimated records", () => {
    assert.equal(getPurchasedPresentationLabel({ origen_dato: "ESTIMADO" }), "No aplica");
    assert.equal(getPurchasedPresentationLabel({ origen_dato: "REAL" }), "Sin dato");
  });
});
