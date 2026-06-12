"""STAGE 2B - Simple Isolation Forest Risk Model.

Model nay duoc viet nho gon de de bao cao:
- Training baseline la cac tinh huong exposure binh thuong/thap.
- Isolation trees tach mau bang feature va threshold ngau nhien.
- Mau bi co lap voi duong di ngan hon duoc xem la bat thuong hon.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from risk.risk_config import FEATURE_NAMES, FEATURE_WEIGHTS


# MARK: Baseline data
# Format: features follow FEATURE_NAMES. Cac sample nay dai dien cho exposure
# binh thuong trong lab/localhost. Isolation Forest hoc baseline nay, sau do
# target co nhieu dau hieu bat thuong hon se co anomaly score cao hon.
BASELINE_SAMPLES = [
    [0, 0, 0, 0, 0, 0, 0],
    [1, 0, 0, 0, 1, 0, 0],
    [1, 0, 0, 0, 1, 1, 0],
    [1, 1, 0, 0, 0, 0, 0],
    [2, 0, 0, 0, 1, 0, 1],
    [2, 1, 0, 0, 1, 1, 0],
    [3, 1, 0, 1, 1, 1, 0],
    [3, 1, 0, 0, 2, 1, 1],
]


@dataclass
class IsolationNode:
    """Mot node trong isolation tree."""

    size: int
    depth: int
    feature_index: int | None = None
    threshold: float | None = None
    left: "IsolationNode | None" = None
    right: "IsolationNode | None" = None

    @property
    def is_leaf(self) -> bool:
        return self.feature_index is None or self.left is None or self.right is None


def to_vector(feature_map: dict) -> list[int]:
    """Dua feature_map ve list theo dung thu tu FEATURE_NAMES."""
    return [int(feature_map[name]) for name in FEATURE_NAMES]


def average_path_length(sample_size: int) -> float:
    """He so c(n) trong cong thuc anomaly score cua Isolation Forest."""
    if sample_size <= 1:
        return 0.0
    if sample_size == 2:
        return 1.0

    harmonic = math.log(sample_size - 1) + 0.5772156649
    return 2.0 * harmonic - (2.0 * (sample_size - 1) / sample_size)


class SimpleIsolationForestRiskModel:
    """Isolation Forest toi gian, deterministic, khong can dependency ngoai."""

    def __init__(self, n_trees: int = 64, random_seed: int = 42) -> None:
        self.n_trees = n_trees
        self.random_seed = random_seed
        self.max_depth = 0
        self.trees: list[IsolationNode] = []
        self.training_size = 0

    def fit(self, samples: list[list[int]]) -> None:
        """Fit forest tren baseline samples."""
        if not samples:
            raise ValueError("Isolation Forest requires at least one baseline sample.")

        self.training_size = len(samples)
        self.max_depth = max(1, math.ceil(math.log2(self.training_size)))
        rng = random.Random(self.random_seed)
        self.trees = []

        for _ in range(self.n_trees):
            rows = [list(row) for row in samples]
            rng.shuffle(rows)
            self.trees.append(self._build_tree(rows, depth=0, rng=rng))

    def _build_tree(self, rows: list[list[int]], depth: int, rng: random.Random) -> IsolationNode:
        if depth >= self.max_depth or len(rows) <= 1 or self._all_rows_same(rows):
            return IsolationNode(size=len(rows), depth=depth)

        splittable_features = [
            index
            for index in range(len(FEATURE_NAMES))
            if min(row[index] for row in rows) < max(row[index] for row in rows)
        ]
        if not splittable_features:
            return IsolationNode(size=len(rows), depth=depth)

        feature_index = rng.choice(splittable_features)
        minimum = min(row[feature_index] for row in rows)
        maximum = max(row[feature_index] for row in rows)
        threshold = rng.uniform(minimum, maximum)

        left_rows = [row for row in rows if row[feature_index] < threshold]
        right_rows = [row for row in rows if row[feature_index] >= threshold]
        if not left_rows or not right_rows:
            return IsolationNode(size=len(rows), depth=depth)

        return IsolationNode(
            size=len(rows),
            depth=depth,
            feature_index=feature_index,
            threshold=threshold,
            left=self._build_tree(left_rows, depth + 1, rng),
            right=self._build_tree(right_rows, depth + 1, rng),
        )

    def _all_rows_same(self, rows: list[list[int]]) -> bool:
        first = rows[0]
        return all(row == first for row in rows)

    def path_length(self, vector: list[int], node: IsolationNode) -> float:
        """Tinh do dai duong di cua vector trong mot isolation tree."""
        if node.is_leaf:
            return node.depth + average_path_length(node.size)

        assert node.feature_index is not None
        assert node.threshold is not None
        assert node.left is not None
        assert node.right is not None

        if vector[node.feature_index] < node.threshold:
            return self.path_length(vector, node.left)
        return self.path_length(vector, node.right)

    def anomaly_score(self, vector: list[int]) -> tuple[float, float]:
        """Tra ve anomaly score va average path length."""
        if not self.trees:
            raise ValueError("Isolation Forest has not been fitted.")

        path_lengths = [self.path_length(vector, tree) for tree in self.trees]
        average_length = sum(path_lengths) / len(path_lengths)
        normalizer = average_path_length(self.training_size)
        if normalizer == 0:
            return 0.0, average_length

        score = 2 ** (-average_length / normalizer)
        return round(score, 4), round(average_length, 4)


def exposure_severity(feature_map: dict) -> float:
    """Bo sung calibration de score 0-10 gan voi rui ro network de giai thich."""
    weighted_total = sum(
        feature_map[name] * weight
        for name, weight in FEATURE_WEIGHTS.items()
    )
    return min(1.0, weighted_total / 10.0)


def explain_exposure(feature_map: dict) -> list[dict]:
    """Expose each weighted contribution used by the classroom risk model."""
    # Dung cung FEATURE_WEIGHTS voi exposure_severity de tranh lech logic.
    drivers = [
        {
            "feature": name,
            "value": feature_map[name],
            "weight": weight,
            "contribution": round(feature_map[name] * weight, 3),
        }
        for name, weight in FEATURE_WEIGHTS.items()
        if feature_map[name]
    ]
    return sorted(drivers, key=lambda item: item["contribution"], reverse=True)


def _compute_baseline_anomaly_scores(model: SimpleIsolationForestRiskModel) -> list[float]:
    """Compute anomaly scores for all baseline samples."""
    return [model.anomaly_score(sample)[0] for sample in BASELINE_SAMPLES]


def _baseline_stats(scores: list[float]) -> dict:
    """Compute mean, std, and max from a list of scores."""
    count = len(scores)
    mean = sum(scores) / count
    variance = sum((s - mean) ** 2 for s in scores) / count
    std = variance ** 0.5
    return {"mean": mean, "std": std, "max": max(scores)}


def calibrate_anomaly_score(anomaly_score: float, baseline: dict | None = None) -> float:
    """
    Dynamically calibrate anomaly score using baseline distribution.

    Scores within 1 standard deviation above baseline mean are treated as
    normal (0). Scores further away are scaled to [0, 1] linearly.
    """
    if baseline is None:
        return max(0.0, min(1.0, anomaly_score))

    threshold = baseline["mean"] + baseline["std"]
    if anomaly_score <= threshold:
        return 0.0
    calibrated = (anomaly_score - threshold) / max(1e-9, 1.0 - threshold)
    return max(0.0, min(1.0, calibrated))


def label_from_score(score: int) -> str:
    """Map numeric score sang risk label."""
    if score <= 3:
        return "Low"
    if score <= 6:
        return "Medium"
    return "High"


def predict_with_isolation_forest(feature_map: dict) -> dict:
    """Du doan risk bang Isolation Forest."""
    vector = to_vector(feature_map)
    model = SimpleIsolationForestRiskModel()
    model.fit(BASELINE_SAMPLES)

    anomaly, average_length = model.anomaly_score(vector)
    # Compute baseline statistics once for dynamic calibration
    baseline_scores = _compute_baseline_anomaly_scores(model)
    baseline = _baseline_stats(baseline_scores)
    calibrated_anomaly = calibrate_anomaly_score(anomaly, baseline)
    exposure = exposure_severity(feature_map)
    combined = (calibrated_anomaly * 0.55) + (exposure * 0.45)
    predicted_score = max(0, min(10, round(combined * 10)))

    return {
        "model_name": "SimpleIsolationForestRiskModel",
        "model_type": "unsupervised Isolation Forest anomaly detection",
        "n_trees": model.n_trees,
        "random_seed": model.random_seed,
        "baseline_size": model.training_size,
        "max_depth": model.max_depth,
        "feature_names": FEATURE_NAMES,
        "feature_vector": vector,
        "anomaly_score": anomaly,
        "calibrated_anomaly": round(calibrated_anomaly, 4),
        "baseline_stats": baseline,
        "average_path_length": average_length,
        "exposure_severity": round(exposure, 4),
        "predicted_score": predicted_score,
        "predicted_label": label_from_score(predicted_score),
        "risk_drivers": explain_exposure(feature_map),
    }
