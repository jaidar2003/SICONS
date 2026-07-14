import json

from tests.chat_evaluation import evaluate_cases

if __name__ == "__main__":
    print(json.dumps(evaluate_cases(), indent=2, ensure_ascii=False))
