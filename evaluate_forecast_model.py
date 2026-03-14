"""
Overfishing Forecast Model Evaluation Agent
Loads forecast_predictions.csv, splits by year (train/val/test), computes MAE/RMSE per country
and overall, flags anomalies, plots sample countries. Saves metrics and anomaly CSVs.
"""
import os
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__) or ".", ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Load predictions (Country, Year, Actual, Forecast)
pred_df = pd.read_csv("forecast_predictions.csv")
pred_df["Year"] = pd.to_numeric(pred_df["Year"], errors="coerce").astype(int)

# Define year splits (use int for matching)
train_years = set(range(1950, 2001))
val_years = set(range(2001, 2011))
test_years = set(range(2011, 2026))

# Use country names as in the CSV (e.g. United States of America)
sample_countries = ["Japan", "United States of America", "Norway"]

metrics_rows = []
anomaly_rows = []

for country in pred_df["Country"].unique():
    country_df = pred_df[pred_df["Country"] == country].copy()

    train_df = country_df[country_df["Year"].isin(train_years)]
    val_df = country_df[country_df["Year"].isin(val_years)]
    test_df = country_df[country_df["Year"].isin(test_years)]

    def compute_metrics(df):
        if len(df) == 0:
            return np.nan, np.nan
        # Use only rows with non-NaN Actual (e.g. test has 2019-2025 without actuals)
        valid = df["Actual"].notna()
        if not valid.any():
            return np.nan, np.nan
        a = df.loc[valid, "Actual"].values.astype(float)
        f = df.loc[valid, "Forecast"].values.astype(float)
        mae = mean_absolute_error(a, f)
        rmse = np.sqrt(mean_squared_error(a, f))
        return mae, rmse

    train_mae, train_rmse = compute_metrics(train_df)
    val_mae, val_rmse = compute_metrics(val_df)
    test_mae, test_rmse = compute_metrics(test_df)

    metrics_rows.append({
        "Country": country,
        "Train_MAE": train_mae, "Train_RMSE": train_rmse,
        "Val_MAE": val_mae, "Val_RMSE": val_rmse,
        "Test_MAE": test_mae, "Test_RMSE": test_rmse,
    })

    # Flag extreme deviations: |forecast - last_known_actual| > 2 * std(Actual)
    actuals = country_df["Actual"].values
    std_actual = float(np.nanstd(actuals)) if len(actuals) > 1 else 0.0
    if std_actual == 0:
        std_actual = float(np.nanstd(pred_df["Actual"])) or 1.0
    test_sorted = test_df.sort_values("Year")
    for _, row in test_sorted.iterrows():
        yr = int(row["Year"])
        # For years without actuals (e.g. 2019+), use last known actual
        prev = country_df[country_df["Year"] == yr - 1]
        last_actual = prev["Actual"].iloc[0] if len(prev) else row["Actual"]
        if pd.isna(last_actual):
            known = country_df[country_df["Actual"].notna()]
            if len(known) > 0:
                last_actual = known["Actual"].iloc[-1]
        if pd.isna(last_actual):
            continue
        last_actual = float(last_actual)
        dev = abs(float(row["Forecast"]) - last_actual)
        if dev > 2 * std_actual:
            anomaly_rows.append({
                "Country": country,
                "Year": yr,
                "Forecast": float(row["Forecast"]),
                "LastActual": float(last_actual),
                "Deviation": float(row["Forecast"] - last_actual),
            })

    # Plot for sample countries
    if country in sample_countries and len(country_df) > 0:
        fig, ax = plt.subplots(figsize=(10, 4))
        years = country_df["Year"].values
        ax.plot(years, country_df["Actual"].values, "o-", label="Actual", markersize=3)
        ax.plot(years, country_df["Forecast"].values, "x--", label="Forecast", markersize=3)
        ax.set_xlabel("Year")
        ax.set_ylabel("Catch (Actual/Forecast)")
        ax.set_title(f"{country} — Actual vs Forecast")
        ax.legend()
        ax.grid(True, alpha=0.3)
        safe = country.replace(" ", "_").replace("/", "_")[:30]
        fig.savefig(f"eval_forecast_{safe}.png", dpi=100)
        plt.close()
        print(f"Saved: eval_forecast_{safe}.png")

# Overall metrics (pool all rows by split)
all_train = pred_df[pred_df["Year"].isin(train_years)]
all_val = pred_df[pred_df["Year"].isin(val_years)]
all_test = pred_df[pred_df["Year"].isin(test_years)]

def overall_metrics(df):
    if len(df) == 0:
        return np.nan, np.nan
    valid = df["Actual"].notna()
    if not valid.any():
        return np.nan, np.nan
    a = df.loc[valid, "Actual"].astype(float)
    f = df.loc[valid, "Forecast"].astype(float)
    return mean_absolute_error(a, f), np.sqrt(mean_squared_error(a, f))

o_train_mae, o_train_rmse = overall_metrics(all_train)
o_val_mae, o_val_rmse = overall_metrics(all_val)
o_test_mae, o_test_rmse = overall_metrics(all_test)

# Overfitting / underfitting highlights
metrics_df = pd.DataFrame(metrics_rows)
overfit = metrics_df[
    (metrics_df["Train_MAE"].notna()) & (metrics_df["Val_MAE"].notna()) &
    (metrics_df["Train_MAE"] * 2 < metrics_df["Val_MAE"])
]
underfit = metrics_df[(metrics_df["Train_MAE"].notna()) & (metrics_df["Train_MAE"] > metrics_df["Val_MAE"].quantile(0.9))]

# Save
metrics_df.to_csv("model_evaluation_metrics.csv", index=False)
anomaly_df = pd.DataFrame(anomaly_rows)
if len(anomaly_df) > 0:
    anomaly_df.to_csv("forecast_anomalies.csv", index=False)
else:
    pd.DataFrame(columns=["Country", "Year", "Forecast", "LastActual", "Deviation"]).to_csv("forecast_anomalies.csv", index=False)

# Print summary
print("\nModel evaluation complete.")
print("Metrics saved to 'model_evaluation_metrics.csv'")
print("Forecast anomalies saved to 'forecast_anomalies.csv'")
print("\nOverall metrics (pooled):")
print(f"  Train: MAE={o_train_mae:.4f}, RMSE={o_train_rmse:.4f}")
print(f"  Val:   MAE={o_val_mae:.4f}, RMSE={o_val_rmse:.4f}")
print(f"  Test:  MAE={o_test_mae:.4f}, RMSE={o_test_rmse:.4f}")
if len(overfit) > 0:
    print(f"\nPossible overfitting (train MAE << val MAE): {len(overfit)} countries")
if len(underfit) > 0:
    print(f"Possible underfitting (high train MAE): {len(underfit)} countries")
print("\n--- Mitigations ---")
print("Overfitting: In forecast_agent.py use simpler ARIMA (VAL_MAE_TIE_TOL=0.08–0.10), or reduce TRAIN_CAP_YEARS.")
print("Underfitting: In forecast_agent.py use more orders / TRAIN_CAP_YEARS=35, or lower VAL_MAE_TIE_TOL=0.03.")
print("Test metrics use only years with actuals (2011-2018); 2019-2025 are forecast-only.")
