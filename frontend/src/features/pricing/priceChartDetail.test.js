import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { buildComparativeChartPoints, getChartPointOrigin } from "./priceChartDetail.js";
import { getDisplayPrice } from "./materialPresentation.js";

describe("price chart detail", () => {
  it("uses the chart values, sorts dates and marks forecast points as estimated", () => {
    const rows = buildComparativeChartPoints({
      serie: [
        { fecha: "2026-02-01", origenes_dato: ["REAL"] },
        { fecha: "2026-01-01", origenes_dato: ["ESTIMADO"] },
      ],
      forecastPoints: [{ fecha: "2026-03-01" }],
      historicalCostPrices: [3210, 3220],
      historicalRetailPrices: [4012.5, 4025],
      forecastCostPrices: [3535],
      forecastRetailPrices: [4418.75],
    });

    assert.deepEqual(rows.map((row) => row.date), ["2026-01-01", "2026-02-01", "2026-03-01"]);
    assert.equal(rows[0].costPrice, 3220);
    assert.equal(rows[1].retailPrice, 4012.5);
    assert.equal(rows[2].origin.label, "Estimado");
    assert.equal(rows[2].isForecast, true);
  });

  it("preserves absent values instead of turning them into zero or NaN", () => {
    const [row] = buildComparativeChartPoints({
      serie: [{ fecha: "2026-01-01", origenes_dato: ["REAL"] }],
      forecastPoints: [],
      historicalCostPrices: [undefined],
      historicalRetailPrices: [Number.NaN],
      forecastCostPrices: [],
      forecastRetailPrices: [],
    });

    assert.equal(row.costPrice, null);
    assert.equal(row.retailPrice, null);
  });

  it("keeps mixed provenance visible", () => {
    assert.equal(getChartPointOrigin(["ESTIMADO", "REAL"]).label, "Observado y estimado");
  });

  it("uses the 25 kg bag presentation for cement cost and retail prices", () => {
    const normalizedCost = 185.3052;
    const retailMargin = 1.2;

    assert.equal(getDisplayPrice(normalizedCost, "Cemento Portland", "kg"), normalizedCost * 25);
    assert.equal(getDisplayPrice(normalizedCost * retailMargin, "Cemento Portland", "kg"), normalizedCost * retailMargin * 25);
  });
});
