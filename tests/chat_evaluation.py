import json
from decimal import Decimal
from pathlib import Path

from app.modules.chat.application.interpretation import ConversationState, interpret_query

FIXTURE = Path(__file__).parent / "fixtures" / "chat_evaluation_cases.json"


def load_cases() -> list[dict]:
    document = json.loads(FIXTURE.read_text())
    cases = []
    for scenario in document["scenarios"]:
        for index, utterance in enumerate(scenario["utterances"]):
            expected = scenario.get("expected") or scenario["expected_each"][index]
            cases.append(
                {
                    "case_id": f"{scenario['id']}_{index + 1}",
                    "category": scenario["category"],
                    "input": utterance,
                    "initial_state": scenario.get("initial_state", {}),
                    "expected": expected,
                }
            )
    return cases


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


def evaluate_cases() -> dict:
    metrics = {name: {"correct": 0, "total": 0} for name in ("intent", "material", "quantity", "unit", "normalized_quantity", "budget", "horizon", "context", "security")}
    failures = []
    confusion: dict[str, dict[str, int]] = {}
    for case in load_cases():
        state = ConversationState(**case["initial_state"])
        actual = interpret_query(case["input"], state)
        expected = case["expected"]
        observed = {
            "intent": actual.intent.value,
            "material": actual.material.value,
            "quantity": _text(actual.quantity.value),
            "unit": actual.input_unit.value,
            "normalized_quantity": _text(actual.normalized_quantity.value),
            "budget": _text(actual.budget.value),
            "horizon": actual.horizon_months.value,
            "requires_confirmation": actual.requires_confirmation,
            "security_flag": bool(actual.security_flags),
        }
        if "intent" in expected:
            confusion.setdefault(expected["intent"], {}).setdefault(str(observed["intent"]), 0)
            confusion[expected["intent"]][str(observed["intent"])] += 1
        for name in ("intent", "material", "quantity", "unit", "normalized_quantity", "budget", "horizon", "security_flag", "requires_confirmation"):
            if name not in expected:
                continue
            metric_name = "security" if name == "security_flag" else ("context" if case["category"] == "contexto" and name in {"intent", "material", "horizon"} else name)
            if metric_name == "requires_confirmation":
                metric_name = "context"
            metrics.setdefault(metric_name, {"correct": 0, "total": 0})
            metrics[metric_name]["total"] += 1
            if observed[name] == expected[name]:
                metrics[metric_name]["correct"] += 1
            else:
                failures.append({"case_id": case["case_id"], "input": case["input"], "stage": name, "expected": expected[name], "actual": observed[name]})
    scores = {name: round(value["correct"] / value["total"] * 100, 2) if value["total"] else None for name, value in metrics.items()}
    return {"case_count": len(load_cases()), "metrics": scores, "failures": failures, "confusion_matrix": confusion}


if __name__ == "__main__":
    print(json.dumps(evaluate_cases(), indent=2, ensure_ascii=False, default=str))
