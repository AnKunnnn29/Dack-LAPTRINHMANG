"""Evaluate the classroom Isolation Forest against a supervised Random Forest."""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, precision_score, recall_score

from risk.risk_config import FEATURE_NAMES
from risk.risk_model import predict_with_isolation_forest


LABELED_SAMPLES = [
    ([0, 0, 0, 0, 0, 0, 0], 0),
    ([1, 0, 0, 0, 1, 0, 0], 0),
    ([2, 0, 0, 0, 1, 0, 1], 0),
    ([2, 1, 0, 0, 1, 1, 1], 0),
    ([3, 1, 0, 0, 2, 1, 2], 0),
    ([3, 2, 0, 1, 1, 1, 0], 0),
    ([4, 2, 1, 1, 1, 2, 1], 1),
    ([5, 3, 1, 2, 2, 2, 2], 1),
    ([6, 4, 2, 2, 2, 3, 3], 1),
    ([8, 5, 2, 3, 3, 4, 4], 1),
    ([10, 6, 3, 3, 4, 5, 5], 1),
    ([12, 7, 3, 3, 5, 6, 6], 1),
]


def _feature_map(vector: list[int]) -> dict:
    return dict(zip(FEATURE_NAMES, vector))


def _metrics(expected: list[int], predicted: list[int]) -> dict:
    tn, fp, fn, tp = confusion_matrix(expected, predicted, labels=[0, 1]).ravel()
    return {
        "precision": round(float(precision_score(expected, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(expected, predicted, zero_division=0)), 4),
        "false_positive_rate": round(float(fp / (fp + tn)) if fp + tn else 0.0, 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def evaluate_models() -> dict:
    """Return reproducible classroom metrics for two risk approaches."""
    vectors = [vector for vector, _ in LABELED_SAMPLES]
    expected = [label for _, label in LABELED_SAMPLES]

    isolation_predictions = [
        int(predict_with_isolation_forest(_feature_map(vector))["predicted_score"] >= 7)
        for vector in vectors
    ]
    supervised = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=4)
    supervised.fit(vectors[::2], expected[::2])
    random_forest_predictions = supervised.predict(vectors).tolist()

    return {
        "dataset": "small labeled classroom exposure scenarios",
        "sample_count": len(vectors),
        "feature_names": FEATURE_NAMES,
        "isolation_forest": _metrics(expected, isolation_predictions),
        "random_forest": _metrics(expected, random_forest_predictions),
        "warning": "Metrics demonstrate the evaluation workflow; use a larger real dataset before production decisions.",
    }
