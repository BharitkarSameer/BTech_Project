from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# Allow `python -m ml.train_crop` from repo root
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import CROP_PROFILES, MODELS_DIR, PUNE_CROPS  # noqa: E402

KAGGLE_URLS = [
    "https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv",
    "https://raw.githubusercontent.com/atharvaingle/Machine-Learning-Projects/master/Crop%20Recommendation/Crop_recommendation.csv",
]

KAGGLE_TO_PUNE = {
    "rice": "rice",
    "maize": "maize",
    "chickpea": "chickpea",
    "grapes": "grapes",
    "cotton": "cotton",
}


def _download_kaggle() -> pd.DataFrame | None:
    import urllib.request

    for url in KAGGLE_URLS:
        try:
            df = pd.read_csv(url)
            df.columns = [c.strip() for c in df.columns]
            label_col = "label" if "label" in df.columns else df.columns[-1]
            df = df.rename(columns={label_col: "label"})
            return df
        except Exception:
            continue
    return None


def _sample_from_profile(crop: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    p = CROP_PROFILES[crop]
    rows = []
    for _ in range(n):
        def span(lo, hi, jitter=0.25):
            mid = (lo + hi) / 2
            width = (hi - lo) * (0.5 + jitter)
            return float(rng.normal(mid, width / 2.5))

        n_v = np.clip(span(*p["n"]), 10, 180)
        p_v = np.clip(span(*p["p"]), 5, 120)
        k_v = np.clip(span(*p["k"]), 10, 200)
        t_v = np.clip(span(*p["temp"]), 8, 42)
        h_v = np.clip(span(*p["hum"]), 20, 99)
        ph_v = np.clip(span(*p["ph"], jitter=0.15), 4.5, 8.8)
        r_v = np.clip(span(*p["rain"], jitter=0.35), 150, 2500)
        rows.append([n_v, p_v, k_v, t_v, h_v, ph_v, r_v, crop])
    return pd.DataFrame(rows, columns=["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"])


def build_dataset() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    frames = []

    kaggle = _download_kaggle()
    if kaggle is not None:
        keep = kaggle[kaggle["label"].str.lower().isin(KAGGLE_TO_PUNE)].copy()
        keep["label"] = keep["label"].str.lower().map(KAGGLE_TO_PUNE)
        frames.append(keep[["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"]])

    for crop in PUNE_CROPS:
        n = 180 if crop not in KAGGLE_TO_PUNE.values() else 80
        frames.append(_sample_from_profile(crop, n, rng))

    df = pd.concat(frames, ignore_index=True)
    df = df[df["label"].isin(PUNE_CROPS)].reset_index(drop=True)
    return df


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = build_dataset()
    out_csv = ROOT / "data" / "crop_training.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    X = df[["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]]
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
    print(classification_report(y_test, pred))
    print(f"accuracy={acc:.4f}")

    joblib.dump(model, MODELS_DIR / "crop_recommender.joblib")
    meta = {
        "features": ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"],
        "classes": list(model.classes_),
        "accuracy": acc,
        "trained_on": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "algorithm": "RandomForestClassifier",
    }
    (MODELS_DIR / "crop_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"saved {MODELS_DIR / 'crop_recommender.joblib'}")


if __name__ == "__main__":
    main()
