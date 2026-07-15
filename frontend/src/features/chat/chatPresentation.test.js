import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { getMessageDetailPresentation } from "./chatPresentation.js";

describe("chat conversational presentation", () => {
  it("keeps the collapsed summary useful and free of internal terminology", () => {
    const result = getMessageDetailPresentation({
      intent: "FORECAST",
      resolvedMaterial: "Cemento Portland",
      resolvedHorizon: 3,
      sources: ["forecast_snapshot"],
      contextUsed: true,
      providerUsed: true,
      provider: "facultad",
    });

    assert.equal(result.summary, "Material: Cemento Portland · Horizonte: 3 meses · 1 fuente");
    assert.doesNotMatch(result.summary, /RAG|fallback|proveedor|intención/i);
  });

  it("explains deterministic calculations in everyday language inside details", () => {
    const result = getMessageDetailPresentation({ intent: "RECOMENDACION", contextUsed: true, sources: [] });
    assert.deepEqual(result.rows.find(([label]) => label === "Cálculos"), ["Cálculos", "Realizados por BuildWise"]);
  });

  it("does not imply that AI calculated a direct deterministic response", () => {
    const result = getMessageDetailPresentation({ intent: "CATALOGO", contextUsed: false, providerUsed: false, sources: [] });
    assert.deepEqual(result.rows.find(([label]) => label === "Redacción"), ["Redacción", "Respuesta directa de BuildWise"]);
  });
});
