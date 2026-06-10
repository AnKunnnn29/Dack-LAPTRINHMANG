"""CLI wrapper for classroom risk model evaluation."""

import json

from risk.evaluate_models import evaluate_models


if __name__ == "__main__":
    print(json.dumps(evaluate_models(), indent=2))
