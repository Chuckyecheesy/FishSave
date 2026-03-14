"""
Downstream ML model for overfishing pipeline.

Inputs (CSVs in project root):
  - train_features_updated.csv  (1950-2000 year cols, OFR, OFR_change, PriceIndex)
  - val_features_updated.csv    (2001-2010 year cols, OFR, OFR_change, PriceIndex)
  - test_features_updated.csv  (2011-2025 year cols, OFR, OFR_change, PriceIndex)

Target: PriceIndex (regression).

Feature windows (fixed 10-year so train/val/test have same input dimension):
  - Train: 1991-2000
  - Val:    2001-2010
  - Test:   2016-2025

Outputs:
  - model.joblib          Fitted sklearn model
  - eval_report.json      Train/val/test MAE & RMSE; optional per-country test metrics

Run: python train_model.py
"""
import json
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib

# Paths (project root = script dir)
ROOT = os.path.dirname(os.path.abspath(__file__))
TRAIN_CSV = os.path.join(ROOT, "train_features_updated.csv")
VAL_CSV = os.path.join(ROOT, "val_features_updated.csv")
TEST_CSV = os.path.join(ROOT, "test_features_updated.csv")
MODEL_PATH = os.path.join(ROOT, "model.joblib")
REPORT_PATH = os.path.join(ROOT, "eval_report.json")

TARGET = "PriceIndex"
TRAIN_YEARS = [str(y) for y in range(1991, 2001)]   # 1991-2000
VAL_YEARS = [str(y) for y in range(2001, 2011)]      # 2001-2010
TEST_YEARS = [str(y) for y in range(2016, 2026)]     # 2016-2025


def load_split(path, year_cols):
    """Load CSV and extract feature matrix X and target y. Keep Country for per-country metrics."""
    df = pd.read_csv(path)
    # Normalize year column names to string
    for c in list(df.columns):
        if isinstance(c, (int, float)) and str(int(c)) in year_cols:
            df = df.rename(columns={c: str(int(c))})
    available = [c for c in year_cols if c in df.columns]
    X = df[available].astype(float)
    X = X.fillna(X.median())
    y = pd.to_numeric(df[TARGET], errors="coerce").fillna(df[TARGET].median())
    countries = df["Country"] if "Country" in df.columns else None
    return X, y, countries, available


def main():
    # Load splits with fixed 10-year windows
    X_train, y_train, countries_train, _ = load_split(TRAIN_CSV, TRAIN_YEARS)
    X_val, y_val, countries_val, _ = load_split(VAL_CSV, VAL_YEARS)
    X_test, y_test, countries_test, _ = load_split(TEST_CSV, TEST_YEARS)

    # Align columns: use only columns present in train (model input dimension)
    # Val and test must have same columns as train; they are already 10 years each
    assert X_train.shape[1] == 10, "Train should have 10 feature columns (1991-2000)"
    assert X_val.shape[1] == 10, "Val should have 10 feature columns (2001-2010)"
    assert X_test.shape[1] == 10, "Test should have 10 feature columns (2016-2025)"

    # Use numpy arrays so feature names don't differ across splits (train 1991-2000, val 2001-2010, test 2016-2025)
    X_train_np = X_train.to_numpy()
    X_val_np = X_val.to_numpy()
    X_test_np = X_test.to_numpy()

    # Train
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train_np, y_train)

    # Predict
    pred_train = model.predict(X_train_np)
    pred_val = model.predict(X_val_np)
    pred_test = model.predict(X_test_np)

    # Metrics
    def mae_rmse(y_true, y_pred):
        return {
            "MAE": float(mean_absolute_error(y_true, y_pred)),
            "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        }

    report = {
        "target": TARGET,
        "feature_windows": {"train": "1991-2000", "val": "2001-2010", "test": "2016-2025"},
        "summary": {
            "train": mae_rmse(y_train, pred_train),
            "val": mae_rmse(y_val, pred_val),
            "test": mae_rmse(y_test, pred_test),
        },
    }

    # Per-country test metrics
    if countries_test is not None and len(countries_test) == len(y_test):
        per_country = []
        for i, country in enumerate(countries_test):
            per_country.append({
                "Country": str(country),
                "MAE": float(mean_absolute_error([y_test.iloc[i]], [pred_test[i]])),
                "RMSE": float(np.sqrt(mean_squared_error([y_test.iloc[i]], [pred_test[i]]))),
            })
        report["per_country_test"] = per_country

    # Save
    joblib.dump(model, MODEL_PATH)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print("Model saved:", MODEL_PATH)
    print("Report saved:", REPORT_PATH)
    print("\nSummary:")
    for split, metrics in report["summary"].items():
        print(f"  {split}: MAE={metrics['MAE']:.4f}, RMSE={metrics['RMSE']:.4f}")


if __name__ == "__main__":
    main()
