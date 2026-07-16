import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { formatUnderstanding, getFollowUpSuggestions, getMissingDataPrompt, getRecoverableChatError, splitProgressiveAnswer, updateCommercialDraftContext } from "./chatExperience.js";

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

  it("uses suggestions returned for the current conversational state", () => {
    assert.deepEqual(
      getFollowUpSuggestions({ intent: "FORECAST", suggestions: ["Cambiar material", "Ver fuente"] }),
      ["Cambiar material", "Ver fuente"],
    );
  });

  it("formats the editable understanding without internal terminology", () => {
    assert.equal(
      formatUnderstanding({
        material: "Cemento Portland",
        quantity: "30",
        input_unit: "bag",
        budget: "200000",
        horizon_months: 3,
      }),
      "Cemento Portland · 30 bolsas · presupuesto $200000 · 3 meses",
    );
  });

  it("separates the result from progressive explanation", () => {
    assert.deepEqual(splitProgressiveAnswer("Resultado principal.\n\nExplicación breve.\n\nPróximo paso."), {
      result: "Resultado principal.",
      explanation: ["Explicación breve.", "Próximo paso."],
    });
  });

  it("clears incompatible purchase values when material changes", () => {
    assert.deepEqual(
      updateCommercialDraftContext(
        { materialId: "1", quantity: "30", budget: "200000", horizon: "3", request: "cemento" },
        "materialId",
        "2",
      ),
      { materialId: "2", quantity: "", budget: "", horizon: "3", request: "" },
    );
  });
});
