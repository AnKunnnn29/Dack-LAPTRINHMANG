"""Unsupervised ML anomaly detection for raw security log lines.

Each log event is converted into a small explainable numeric feature vector.
Isolation Forest is then fitted on the selected log file itself, so public
Loghub data is genuinely used as ML training data without requiring labels.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = [
    "message_length",
    "token_count",
    "digit_ratio",
    "special_ratio",
    "uppercase_ratio",
    "unique_token_ratio",
    "ip_address_count",
    "path_depth",
    "error_keyword_count",
    "security_keyword_count",
    "template_rarity",
    "event_type_rarity",
]

ERROR_KEYWORDS = ("error", "failed", "failure", "denied", "invalid", "fatal", "warning")
SECURITY_KEYWORDS = (
    "break-in",
    "attack",
    "exploit",
    "password",
    "authentication",
    "unauthorized",
    "malware",
    "union select",
    "../",
)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./:-]+")
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
NUMBER_PATTERN = re.compile(r"\b\d+\b")
HEX_PATTERN = re.compile(r"\b[0-9a-fA-F]{8,}\b")


def _message(event: dict[str, Any]) -> str:
    return " ".join(
        str(event.get(name, ""))
        for name in ("event_type", "process", "command_line", "path", "message")
        if event.get(name)
    )


def _template(text: str) -> str:
    """Normalize volatile values so rarity reflects log-event structure."""
    normalized = IP_PATTERN.sub("<IP>", text.lower())
    normalized = HEX_PATTERN.sub("<HEX>", normalized)
    normalized = NUMBER_PATTERN.sub("<NUM>", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _rarity(total: int, frequency: int) -> float:
    return round(math.log1p(total / max(1, frequency)), 6)


def extract_log_features(events: list[dict[str, Any]]) -> tuple[list[list[float]], list[dict[str, float]]]:
    """Convert parsed events into explainable per-line feature vectors."""
    messages = [_message(event) for event in events]
    templates = [_template(message) for message in messages]
    template_counts = Counter(templates)
    event_type_counts = Counter(str(event.get("event_type", "unknown")) for event in events)
    total = len(events)
    vectors: list[list[float]] = []
    feature_maps: list[dict[str, float]] = []

    for event, message, template in zip(events, messages, templates):
        lowered = message.lower()
        tokens = TOKEN_PATTERN.findall(message)
        length = max(1, len(message))
        alpha_count = max(1, sum(char.isalpha() for char in message))
        event_type = str(event.get("event_type", "unknown"))
        feature_map = {
            "message_length": float(len(message)),
            "token_count": float(len(tokens)),
            "digit_ratio": round(sum(char.isdigit() for char in message) / length, 6),
            "special_ratio": round(sum(not char.isalnum() and not char.isspace() for char in message) / length, 6),
            "uppercase_ratio": round(sum(char.isupper() for char in message) / alpha_count, 6),
            "unique_token_ratio": round(len(set(token.lower() for token in tokens)) / max(1, len(tokens)), 6),
            "ip_address_count": float(len(IP_PATTERN.findall(message))),
            "path_depth": float(message.count("/") + message.count("\\")),
            "error_keyword_count": float(sum(lowered.count(keyword) for keyword in ERROR_KEYWORDS)),
            "security_keyword_count": float(sum(lowered.count(keyword) for keyword in SECURITY_KEYWORDS)),
            "template_rarity": _rarity(total, template_counts[template]),
            "event_type_rarity": _rarity(total, event_type_counts[event_type]),
        }
        feature_maps.append(feature_map)
        vectors.append([feature_map[name] for name in FEATURE_NAMES])

    return vectors, feature_maps


def analyze_log_anomalies(
    events: list[dict[str, Any]],
    contamination: float = 0.03,
    top_limit: int = 20,
) -> dict[str, Any]:
    """Fit Isolation Forest on log events and return ranked anomaly candidates."""
    if not 0 < contamination <= 0.5:
        raise ValueError("ML contamination must be greater than 0 and at most 0.5.")
    if top_limit < 1:
        raise ValueError("ML top_limit must be at least 1.")
    if len(events) < 8:
        return {
            "status": "skipped",
            "reason": "At least 8 log events are required for anomaly detection.",
            "model_name": "IsolationForest",
            "trained_on_event_count": len(events),
            "feature_names": FEATURE_NAMES,
            "anomaly_count": 0,
            "top_anomalies": [],
        }

    vectors, feature_maps = extract_log_features(events)
    scaled_vectors = StandardScaler().fit_transform(vectors)
    model = IsolationForest(
        n_estimators=150,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    predictions = model.fit_predict(scaled_vectors)
    decision_scores = model.decision_function(scaled_vectors)
    raw_anomaly_scores = [-float(score) for score in decision_scores]
    minimum = min(raw_anomaly_scores)
    maximum = max(raw_anomaly_scores)
    span = maximum - minimum

    ranked = []
    for event, feature_map, prediction, raw_score in zip(
        events,
        feature_maps,
        predictions,
        raw_anomaly_scores,
    ):
        if int(prediction) != -1:
            continue
        normalized_score = 1.0 if span == 0 else (raw_score - minimum) / span
        ranked.append(
            {
                "line_number": event.get("line_number"),
                "anomaly_score": round(normalized_score, 6),
                "raw_decision_score": round(raw_score, 6),
                "event_type": event.get("event_type", "unknown"),
                "message": str(event.get("message", ""))[:500],
                "features": feature_map,
            }
        )

    ranked.sort(key=lambda item: item["raw_decision_score"], reverse=True)
    return {
        "status": "completed",
        "model_name": "IsolationForest",
        "model_type": "unsupervised per-log-line anomaly detection",
        "trained_on_event_count": len(events),
        "n_estimators": 150,
        "random_state": 42,
        "contamination": contamination,
        "feature_names": FEATURE_NAMES,
        "anomaly_count": len(ranked),
        "anomaly_rate": round(len(ranked) / len(events), 6),
        "top_anomalies": ranked[:top_limit],
        "notes": [
            "The model is fitted directly on the selected log file.",
            "Anomalies are candidates for human review, not proof of an attack.",
            "Isolation Forest does not require labeled training data.",
        ],
    }
