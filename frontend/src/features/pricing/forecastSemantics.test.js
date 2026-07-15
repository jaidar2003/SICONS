import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { getMapePresentation } from "./forecastMetrics.js";
import { getSummaryDecisionPresentation } from "./summarySemantics.js";

const risingForecast = {
  ultimo_precio_observado: "100",
  puntos: [{ precio_proyectado: "110" }],
};

const fallingForecast = {
  ultimo_precio_observado: "100",
  puntos: [{ precio_proyectado: "90" }],
};

describe("deterministic recommendation semantics", () => {
  it("shows a buy decision only when it comes from the backend", () => {
    const result = getSummaryDecisionPresentation({
      recommendation: { decision: "COMPRAR_AHORA", justificacion: "Supera el umbral determinístico." },
      forecast: fallingForecast,
    });

    assert.equal(result.kind, "backend-recommendation");
    assert.equal(result.title, "Comprar ahora");
    assert.equal(result.description, "Supera el umbral determinístico.");
  });

  it("shows a wait decision only when it comes from the backend", () => {
    const result = getSummaryDecisionPresentation({
      recommendation: { decision: "ESPERAR", justificacion: "Decisión calculada por contexto." },
      forecast: risingForecast,
    });

    assert.equal(result.title, "Esperar");
    assert.equal(result.description, "Decisión calculada por contexto.");
  });

  it("uses descriptive trend copy when no backend recommendation exists", () => {
    const result = getSummaryDecisionPresentation({ forecast: risingForecast });

    assert.equal(result.kind, "trend");
    assert.equal(result.eyebrow, "Tendencia esperada");
    assert.match(result.provenance, /no constituye/i);
    assert.doesNotMatch(`${result.title} ${result.description}`, /comprar|esperar|anticipar|postergar/i);
  });

  it("never overrides a backend decision with the forecast direction", () => {
    const positiveButWait = getSummaryDecisionPresentation({
      recommendation: { decision: "ESPERAR", justificacion: "Backend" },
      forecast: risingForecast,
    });
    const negativeButBuy = getSummaryDecisionPresentation({
      recommendation: { decision: "COMPRAR_AHORA", justificacion: "Backend" },
      forecast: fallingForecast,
    });

    assert.equal(positiveButWait.title, "Esperar");
    assert.equal(negativeButBuy.title, "Comprar ahora");
  });
});

describe("MAPE presentation", () => {
  it("shows the original backend value in Argentine format", () => {
    const result = getMapePresentation(4.22);

    assert.equal(result.value, "4,22%");
    assert.match(result.label, /Error porcentual promedio/);
    assert.match(result.explanation, /menor fue el error promedio/i);
    assert.match(result.explanation, /No es una probabilidad/i);
    assert.doesNotMatch(`${result.label} ${result.value} ${result.explanation}`, /efectividad|95,78/i);
  });

  it("handles zero without claiming certainty", () => {
    const result = getMapePresentation(0);
    assert.equal(result.value, "0,00%");
    assert.match(result.explanation, /garantiza/i);
  });

  it("handles missing and extreme values without deriving effectiveness", () => {
    assert.equal(getMapePresentation(null).value, "Sin dato");
    assert.equal(getMapePresentation(undefined).value, "Sin dato");
    assert.equal(getMapePresentation(150).value, "150,00%");
  });
});
