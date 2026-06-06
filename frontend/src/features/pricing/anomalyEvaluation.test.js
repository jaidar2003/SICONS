import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { parseConfirmedAnomalyDates } from "./anomalyEvaluation.js";

describe("anomaly evaluation helpers", () => {
  it("normalizes monthly and daily dates while removing duplicates", () => {
    const result = parseConfirmedAnomalyDates("2026-02\n2026-02-01\n2026-05-10\n2026-05-10");

    assert.deepEqual(result.dates, ["2026-02-01", "2026-05-10"]);
    assert.deepEqual(result.invalidValues, []);
  });

  it("reports invalid entries", () => {
    const result = parseConfirmedAnomalyDates("2026-13-01\nfoo\n2026-02-30");

    assert.deepEqual(result.dates, []);
    assert.deepEqual(result.invalidValues, ["2026-13-01", "foo", "2026-02-30"]);
  });
});
