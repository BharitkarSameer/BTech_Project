from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from backend.config import (
    CROP_EMOJI,
    CROP_INFO,
    CROP_PROFILES,
    MODELS_DIR,
    MODEL_BLEND_ML_WEIGHT,
    MODEL_BLEND_RULE_WEIGHT,
    PUNE_CROPS,
)

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

_model = None
_meta: dict | None = None


def _load():
    global _model, _meta
    if _model is not None:
        return
    model_path = MODELS_DIR / "crop_recommender.joblib"
    meta_path = MODELS_DIR / "crop_meta.json"
    if not model_path.exists():
        raise FileNotFoundError(
            "Crop model missing. Run `python -m ml.train_crop` from the project root."
        )
    _model = joblib.load(model_path)
    _meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"classes": list(_model.classes_)}


def _range_score(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 50.0
    if low <= value <= high:
        return 100.0
    span = high - low if high > low else 1.0
    dist = (low - value) / span if value < low else (value - high) / span
    return max(0.0, 100.0 - dist * 100.0)


def rule_scores(
    N: float, P: float, K: float, temperature: float, humidity: float, ph: float, rainfall: float
) -> dict[str, float]:
    out = {}
    for crop, profile in CROP_PROFILES.items():
        s = (
            _range_score(ph, *profile["ph"])
            + _range_score(N, *profile["n"])
            + _range_score(P, *profile["p"])
            + _range_score(K, *profile["k"])
            + _range_score(temperature, *profile["temp"])
            + _range_score(humidity, *profile["hum"])
            + _range_score(rainfall, *profile["rain"])
        ) / 7.0
        out[crop] = s / 100.0  # 0–1
    return out


def recommend_crops(
    N: float,
    P: float,
    K: float,
    temperature: float,
    humidity: float,
    ph: float,
    rainfall: float,
    top_k: int = 5,
) -> list[dict]:
    _load()
    x = pd.DataFrame([[N, P, K, temperature, humidity, ph, rainfall]], columns=FEATURES)
    proba = _model.predict_proba(x)[0]
    classes = list(_model.classes_)
    ml = {str(c): float(p) for c, p in zip(classes, proba)}

    rules = rule_scores(N, P, K, temperature, humidity, ph, rainfall)
    blended: dict[str, float] = {}
    for crop in PUNE_CROPS:
        m = ml.get(crop, 0.0)
        r = rules.get(crop, 0.0)
        blended[crop] = MODEL_BLEND_ML_WEIGHT * m + MODEL_BLEND_RULE_WEIGHT * r

    ranked = sorted(blended.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    results = []
    for crop, score in ranked:
        results.append(
            {
                "crop": crop,
                "score": round(score, 4),
                "confidence_pct": round(min(score * 100, 99.0), 1),
                "season": CROP_PROFILES[crop]["season"],
                "emoji": CROP_EMOJI.get(crop, "🌱"),
                "info": CROP_INFO.get(crop, ""),
                "ml_probability": round(ml.get(crop, 0.0), 4),
                "rule_score": round(rules.get(crop, 0.0), 4),
            }
        )
    return results
