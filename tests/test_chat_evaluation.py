import pytest

from tests.chat_evaluation import evaluate_cases, load_cases


@pytest.mark.chat_evaluation
def test_canonical_chat_evaluation_meets_quality_gates() -> None:
    report = evaluate_cases()
    assert report["case_count"] == 120
    assert report["metrics"]["intent"] >= 97
    assert report["metrics"]["material"] >= 98
    assert report["metrics"]["quantity"] >= 98
    assert report["metrics"]["unit"] >= 98
    assert report["metrics"]["normalized_quantity"] >= 98
    assert report["metrics"]["budget"] >= 98
    assert report["metrics"]["horizon"] >= 97
    assert report["metrics"]["context"] >= 95
    assert report["metrics"]["security"] == 100


def test_case_ids_are_unique() -> None:
    cases = load_cases()
    assert len({case["case_id"] for case in cases}) == len(cases)
