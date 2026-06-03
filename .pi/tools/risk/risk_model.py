"""STAGE 2B - Simple KNN Risk Model.

Model nay duoc viet nho gon de de bao cao:
- Training samples la cac tinh huong mau.
- Feature vector duoc so sanh bang Euclidean distance.
- 3 mau gan nhat quyet dinh risk label va risk score.
"""

import math

from risk.risk_config import FEATURE_NAMES


# MARK: Training data
# Format: features follow FEATURE_NAMES, score is 0-10, label is Low/Medium/High.
TRAINING_SAMPLES = [
    {"features": [0, 0, 0, 0, 0, 0, 0], "score": 0, "label": "Low"},
    {"features": [1, 0, 0, 0, 1, 0, 0], "score": 2, "label": "Low"},
    {"features": [2, 0, 0, 0, 1, 0, 1], "score": 3, "label": "Low"},
    {"features": [2, 1, 0, 0, 1, 0, 0], "score": 5, "label": "Medium"},
    {"features": [3, 1, 0, 0, 2, 1, 1], "score": 6, "label": "Medium"},
    {"features": [3, 1, 0, 1, 1, 1, 0], "score": 7, "label": "Medium"},
    {"features": [4, 2, 1, 1, 1, 2, 0], "score": 8, "label": "High"},
    {"features": [5, 3, 1, 2, 2, 3, 0], "score": 9, "label": "High"},
    {"features": [6, 3, 1, 3, 3, 5, 0], "score": 10, "label": "High"},
    {"features": [8, 4, 2, 3, 3, 5, 2], "score": 10, "label": "High"},
]


def to_vector(feature_map: dict) -> list[int]:
    """Dua feature_map ve list theo dung thu tu FEATURE_NAMES."""
    return [int(feature_map[name]) for name in FEATURE_NAMES]


def euclidean_distance(left: list[int], right: list[int]) -> float:
    """Tinh khoang cach Euclidean giua 2 vector."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def predict_with_knn(feature_map: dict, k: int = 3) -> dict:
    """Du doan risk bang K-Nearest Neighbors."""
    vector = to_vector(feature_map)
    distances = []

    # MARK: Distance calculation - so sanh input voi tung sample mau.
    for sample in TRAINING_SAMPLES:
        distances.append(
            {
                "distance": euclidean_distance(vector, sample["features"]),
                "features": sample["features"],
                "score": sample["score"],
                "label": sample["label"],
            }
        )

    # MARK: Select neighbors - lay k mau gan nhat.
    neighbors = sorted(distances, key=lambda item: item["distance"])[:k]
    label_counts = {}
    for neighbor in neighbors:
        label = neighbor["label"]
        label_counts[label] = label_counts.get(label, 0) + 1

    top_count = max(label_counts.values())
    tied_labels = [label for label, count in label_counts.items() if count == top_count]
    predicted_label = neighbors[0]["label"]
    for label in tied_labels:
        if label == neighbors[0]["label"]:
            predicted_label = label
            break

    # Diem rui ro la trung binh score cua cac neighbor.
    predicted_score = round(sum(item["score"] for item in neighbors) / len(neighbors))

    return {
        "model_name": "SimpleKNNRiskModel",
        "model_type": "supervised K-Nearest Neighbors",
        "k": k,
        "feature_names": FEATURE_NAMES,
        "feature_vector": vector,
        "predicted_score": predicted_score,
        "predicted_label": predicted_label,
        "nearest_samples": neighbors,
    }
