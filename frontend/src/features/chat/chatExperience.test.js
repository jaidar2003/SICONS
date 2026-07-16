import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { getFollowUpSuggestions, getMissingDataPrompt, getRecoverableChatError } from "./chatExperience.js";

describe("chat follow-up experience", () => {
  it("offers relevant forecast follow-ups without internal terminology", () => {
    const suggestions = getFollowUpSuggestions({ intent: "FORECAST" });
    assert.deepEqual(suggestions, ["¿Y a 6 meses?", "¿Qué significa el MAPE?", "¿Me conviene comprar?"]);
    assert.doesNotMatch(suggestions.join(" "), /RAG|snapshot|fallback|proveedor/i);
  });

  it("does not suggest follow-ups for rejected messages", () => {
    assert.deepEqual(getFollowUpSuggestions({ intent: "FUERA_ALCANCE", rejected: true }), []);
  });

  it("turns infrastructure failures into an actionable message", () => {
    assert.equal(
      getRecoverableChatError(new Error("API 503: /chat/consultas")),
      "BuildWise no está disponible temporalmente. Tu consulta no se perdió y podés reintentar.",
    );
  });

  it("asks only the first field that unlocks a purchase", () => {
    assert.equal(
      getMissingDataPrompt(["cantidad", "fecha_objetivo_uso_o_horizonte_meses"]),
      "¿Que cantidad necesitas? Podes indicarla en bolsas, kilogramos u otra unidad disponible.",
    );
  });

  it("does not require a budget when quantity is enough", () => {
    assert.doesNotMatch(getMissingDataPrompt([]), /presupuesto/i);
  });
});
