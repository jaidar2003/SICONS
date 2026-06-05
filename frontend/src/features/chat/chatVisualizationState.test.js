import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  INSUFFICIENT_CHART_DATA_MESSAGE,
  shouldShowInsufficientChartDataMessage,
} from "./chatVisualizationState.js";

describe("chat visualization empty state", () => {
  it("shows the insufficient data message when there is no serie or forecast", () => {
    assert.equal(
      shouldShowInsufficientChartDataMessage({
        loading: false,
        error: "",
        serie: [],
        forecast: { puntos: [] },
      }),
      true
    );
    assert.equal(INSUFFICIENT_CHART_DATA_MESSAGE, "No hay datos suficientes en BuildWise para graficar este material.");
  });

  it("does not show the message when historical serie has points", () => {
    assert.equal(
      shouldShowInsufficientChartDataMessage({
        serie: [{ fecha: "2026-01-01", precio_promedio_normalizado: 100 }],
        forecast: null,
      }),
      false
    );
  });

  it("does not show the message when forecast has points", () => {
    assert.equal(
      shouldShowInsufficientChartDataMessage({
        serie: [],
        forecast: { puntos: [{ fecha: "2026-02-01", precio_proyectado: 120 }] },
      }),
      false
    );
  });

  it("does not show the message while loading or when a chart error exists", () => {
    assert.equal(shouldShowInsufficientChartDataMessage({ loading: true, serie: [], forecast: null }), false);
    assert.equal(shouldShowInsufficientChartDataMessage({ error: "fallo endpoint", serie: [], forecast: null }), false);
  });
});
