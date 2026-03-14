"""
Time-Series Forecasting Agent for Overfishing Project
Forecasts catch (year columns) per country using ARIMA on train, evaluates on val/test.
Saves forecast_predictions.csv, forecast_metrics.csv, and optional plots.
"""
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import warnings

# ARIMA: statsmodels 0.12+ uses tsa.arima.model
try:
    from statsmodels.tsa.arima.model import ARIMA
except ImportError:
    try:
        from statsmodels.tsa.arima_model import ARIMA
    except ImportError:
        ARIMA = None

# Load CSVs
train_df = pd.read_csv('train_features.csv')
val_df = pd.read_csv('val_features.csv')
test_df = pd.read_csv('test_features.csv')

# Detect and sort year columns
def get_year_cols(df):
    cols = [c for c in df.columns if isinstance(c, str) and c.isdigit()]
    return sorted(cols, key=int)

train_years = get_year_cols(train_df)
val_years = get_year_cols(val_df)
test_years = get_year_cols(test_df)

# Target is the catch time series (year columns), not OFR/PriceIndex (single value per country)
# Balance overfitting vs underfitting: prefer simpler (tie_tol), moderate train window, one extra order tier.
TRAIN_CAP_YEARS = 18  # last N years: 18 balances signal (less underfitting) vs noise (less overfitting)
ORDERS_BY_SIMPLICITY = [
    (0, 1, 0), (0, 1, 1), (1, 1, 1),   # base set
    (1, 1, 2), (2, 1, 1),              # one extra tier for structure; (2,1,2) removed to curb overfitting
]
VAL_MAE_TIE_TOL = 0.12  # prefer simpler when val MAE within 12% (balance: allow complex when they help, bias simpler)

predictions_list = []
metrics_list = []
plot_countries = ['Japan', 'United States of America', 'Norway']


def fit_arima_and_forecast(y_train, order, steps_val, steps_test):
    """Fit ARIMA with given order; return (model_fit, val_forecast, test_forecast) or (None, None, None)."""
    if ARIMA is None or len(y_train) < 5:
        return None, None, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = ARIMA(y_train, order=order)
            model_fit = model.fit()
            val_f = model_fit.forecast(steps=steps_val)
            full = model_fit.forecast(steps=steps_val + steps_test)
            test_f = full[-steps_test:]
            return model_fit, val_f, test_f
        except Exception:
            return None, None, None


for idx, country in enumerate(train_df['Country']):
    # Time series: one value per year (catch)
    y_train_full = train_df.loc[train_df['Country'] == country, train_years].values.flatten()
    y_train_full = np.nan_to_num(pd.to_numeric(y_train_full, errors='coerce'), nan=np.nanmean(y_train_full))
    y_val = np.asarray(val_df.loc[val_df['Country'] == country, val_years].values.flatten(), dtype=float)
    y_test = np.asarray(test_df.loc[test_df['Country'] == country, test_years].values.flatten(), dtype=float)

    # Optional: cap training to last TRAIN_CAP_YEARS years; use capped if val is not worse (within 5%)
    if TRAIN_CAP_YEARS is not None and len(y_train_full) > TRAIN_CAP_YEARS:
        y_train_short = np.asarray(y_train_full[-TRAIN_CAP_YEARS:], dtype=float)
        best_val_mae_full = np.inf
        best_order_full = None
        for order in ORDERS_BY_SIMPLICITY:
            mf, vf, _ = fit_arima_and_forecast(y_train_full, order, len(y_val), len(y_test))
            if vf is not None:
                mae = mean_absolute_error(y_val, vf)
                if mae < best_val_mae_full:
                    best_val_mae_full = mae
                    best_order_full = order
        best_val_mae_short = np.inf
        best_order_short = None
        for order in ORDERS_BY_SIMPLICITY:
            mf, vf, _ = fit_arima_and_forecast(y_train_short, order, len(y_val), len(y_test))
            if vf is not None:
                mae = mean_absolute_error(y_val, vf)
                if mae < best_val_mae_short:
                    best_val_mae_short = mae
                    best_order_short = order
        # Use capped train if val MAE is not worse (within tie tolerance)
        if best_val_mae_short <= best_val_mae_full * (1 + VAL_MAE_TIE_TOL):
            y_train = y_train_short
            train_years_used = train_years[-TRAIN_CAP_YEARS:]
        else:
            y_train = y_train_full
            train_years_used = train_years
    else:
        y_train = np.asarray(y_train_full, dtype=float)
        train_years_used = train_years

    val_forecast = None
    test_forecast = None
    model_fit = None
    chosen_order = None

    # Select order by validation MAE; prefer simpler when within VAL_MAE_TIE_TOL
    best_val_mae = np.inf
    candidates = []  # (order, model_fit, val_forecast, test_forecast, val_mae)
    for order in ORDERS_BY_SIMPLICITY:
        mf, vf, tf = fit_arima_and_forecast(y_train, order, len(y_val), len(y_test))
        if vf is not None:
            mae = mean_absolute_error(y_val, vf)
            candidates.append((order, mf, vf, tf, mae))
    if candidates:
        best_mae = min(c[4] for c in candidates)
        # Sort by simplicity (p+q), then pick first that is within 5% of best val MAE
        candidates.sort(key=lambda x: (x[0][0] + x[0][2], x[4]))
        for order, mf, vf, tf, mae in candidates:
            if mae <= best_mae * (1 + VAL_MAE_TIE_TOL):
                model_fit, val_forecast, test_forecast = mf, vf, tf
                chosen_order = order
                break

    # Fallback: naive forecast (last known value repeated)
    if val_forecast is None:
        last = float(y_train[-1]) if len(y_train) else 0.0
        val_forecast = np.full(len(y_val), last)
        test_forecast = np.full(len(y_test), last)

    # In-sample train "forecast" for evaluation (train metrics, overfitting check)
    if model_fit is not None and hasattr(model_fit, 'fittedvalues'):
        train_forecast = np.asarray(model_fit.fittedvalues, dtype=float)
    else:
        train_forecast = np.asarray(y_train, dtype=float)  # naive: use actual so no train forecast
    if len(train_forecast) != len(y_train):
        train_forecast = np.asarray(y_train, dtype=float)
    # Align to train_years_used (we may have capped train)
    n_train = len(train_years_used)
    if len(y_train) != n_train or len(train_forecast) != n_train:
        y_train = np.asarray(y_train[:n_train], dtype=float) if len(y_train) >= n_train else np.asarray(y_train, dtype=float)
        train_forecast = np.asarray(train_forecast[:n_train], dtype=float) if len(train_forecast) >= n_train else np.asarray(train_forecast, dtype=float)
    y_train = y_train[:n_train]
    train_forecast = train_forecast[:n_train]

    val_mae = mean_absolute_error(y_val, val_forecast)
    val_rmse = np.sqrt(mean_squared_error(y_val, val_forecast))
    test_mae = mean_absolute_error(y_test, test_forecast)
    test_rmse = np.sqrt(mean_squared_error(y_test, test_forecast))

    metrics_list.append({
        'Country': country,
        'Val_MAE': round(val_mae, 4),
        'Val_RMSE': round(val_rmse, 4),
        'Test_MAE': round(test_mae, 4),
        'Test_RMSE': round(test_rmse, 4),
    })

    for i, year in enumerate(train_years_used):
        predictions_list.append({
            'Country': country,
            'Year': int(year),
            'Actual': float(y_train[i]),
            'Forecast': float(train_forecast[i]),
        })
    for i, year in enumerate(val_years):
        predictions_list.append({
            'Country': country,
            'Year': int(year),
            'Actual': float(y_val[i]),
            'Forecast': float(val_forecast[i]),
        })
    for i, year in enumerate(test_years):
        predictions_list.append({
            'Country': country,
            'Year': int(year),
            'Actual': float(y_test[i]),
            'Forecast': float(test_forecast[i]),
        })

    # Plot for sample countries
    if country in plot_countries:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(list(map(int, train_years_used)), y_train, 'C0-', label='Train (actual)', lw=2)
        ax.plot(list(map(int, val_years)), y_val, 'C1-o', label='Val (actual)', markersize=4)
        ax.plot(list(map(int, val_years)), val_forecast, 'C1--x', label='Val (forecast)', markersize=4)
        ax.plot(list(map(int, test_years)), y_test, 'C2-o', label='Test (actual)', markersize=4)
        ax.plot(list(map(int, test_years)), test_forecast, 'C2--x', label='Test (forecast)', markersize=4)
        ax.set_xlabel('Year')
        ax.set_ylabel('Catch')
        ax.set_title(f'{country} — Catch: actual vs forecast')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        safe_name = country.replace(' ', '_').replace('/', '_')[:30]
        plt.savefig(f'forecast_{safe_name}.png', dpi=100)
        plt.close()
        print(f"Saved: forecast_{safe_name}.png")

# Save outputs
pred_df = pd.DataFrame(predictions_list)
pred_df.to_csv('forecast_predictions.csv', index=False)
metrics_df = pd.DataFrame(metrics_list)
metrics_df.to_csv('forecast_metrics.csv', index=False)

print("\nForecasting complete.")
print("Predictions: forecast_predictions.csv")
print("Metrics: forecast_metrics.csv")
print("\nSample metrics (first 5 countries):")
print(metrics_df.head().to_string(index=False))
