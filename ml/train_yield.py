from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import MODELS_DIR  # noqa: E402

FEATURES = [
    "crop_id",
    "season_id",
    "year",
    "ndvi_mean",
    "ndvi_max",
    "ndvi_p90",
    "evi_mean",
    "ndwi_mean",
    "scene_count",
    "rainfall_mm",
    "temperature_mean_c",
    "avg_tmax_c",
    "avg_tmin_c",
    "humidity_mean_pct",
    "ph",
    "clay_pct",
    "soc",
]


def main():
    csv_path = ROOT / "data" / "yield_training.csv"
    if not csv_path.exists():
        from ml.build_yield_dataset import main as build

        build()
    df = pd.read_csv(csv_path)
    crops = sorted(df["crop"].unique())
    seasons = sorted(df["season"].unique())
    crop_map = {c: i for i, c in enumerate(crops)}
    season_map = {s: i for i, s in enumerate(seasons)}
    df["crop_id"] = df["crop"].map(crop_map)
    df["season_id"] = df["season"].map(season_map)

    X = df[FEATURES]
    y = df["yield_kg_ha"].astype(float)

    try:
        import lightgbm as lgb

        model = lgb.LGBMRegressor(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            verbosity=-1,
        )
        algo = "LGBMRegressor"
    except Exception:
        from sklearn.ensemble import GradientBoostingRegressor

        model = GradientBoostingRegressor(random_state=42, n_estimators=250, max_depth=4)
        algo = "GradientBoostingRegressor"

    # Leave-one-year-out style: last year as holdout
    holdout_year = int(df["year"].max())
    train_mask = df["year"] < holdout_year
    model.fit(X[train_mask], y[train_mask])
    pred = model.predict(X[~train_mask])
    y_true = y[~train_mask]
    mae = float(mean_absolute_error(y_true, pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, pred)))
    r2 = float(r2_score(y_true, pred))
    print(f"{algo} holdout year {holdout_year}: MAE={mae:.1f} RMSE={rmse:.1f} R2={r2:.3f}")

    residuals = y[train_mask] - model.predict(X[train_mask])
    global_std = float(np.std(residuals))
    residual_std = {}
    train_df = df[train_mask].copy()
    train_df["resid"] = residuals.values
    for crop, g in train_df.groupby("crop"):
        residual_std[crop] = float(np.std(g["resid"])) if len(g) > 3 else global_std

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "crop_map": crop_map, "season_map": season_map},
        MODELS_DIR / "yield_lgbm.joblib",
    )
    meta = {
        "features": FEATURES,
        "algorithm": algo,
        "holdout_year": holdout_year,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "global_residual_std": global_std,
        "residual_std": residual_std,
        "crop_map": crop_map,
        "season_map": season_map,
        "trained_on": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
    }
    (MODELS_DIR / "yield_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"saved {MODELS_DIR / 'yield_lgbm.joblib'}")


if __name__ == "__main__":
    main()
