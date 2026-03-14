"""
Forecast next 5 and next 10 years (from current year) per country using the same
balanced ARIMA config as forecast_agent to avoid over/underfitting.
Outputs two CSVs with only Country, Year, OFR_change, Inflation_pct.
"""
import pandas as pd
import numpy as np
import warnings
from datetime import date

try:
    from statsmodels.tsa.arima.model import ARIMA
except ImportError:
    try:
        from statsmodels.tsa.arima_model import ARIMA
    except ImportError:
        ARIMA = None

from sklearn.metrics import mean_absolute_error

# Same balanced config as forecast_agent (do not overfit or underfit)
TRAIN_CAP_YEARS = 18
ORDERS_BY_SIMPLICITY = [
    (0, 1, 0), (0, 1, 1), (1, 1, 1),
    (1, 1, 2), (2, 1, 1),
]
VAL_MAE_TIE_TOL = 0.12
BETA = 0.5
PRICE_START = 100.0

CURRENT_YEAR = date.today().year
NEXT_5_YEARS = list(range(CURRENT_YEAR + 1, CURRENT_YEAR + 6))
NEXT_10_YEARS = list(range(CURRENT_YEAR + 1, CURRENT_YEAR + 11))

train_df = pd.read_csv("train_features.csv")
val_df = pd.read_csv("val_features.csv")
test_df = pd.read_csv("test_features.csv")


def get_year_cols(df):
    cols = [c for c in df.columns if isinstance(c, str) and c.isdigit()]
    return sorted(cols, key=int)


train_years = get_year_cols(train_df)
val_years = get_year_cols(val_df)
test_years = get_year_cols(test_df)
all_years = sorted(set(train_years) | set(val_years) | set(test_years), key=int)
last_data_year = max(int(y) for y in all_years)
num_future_steps = max(NEXT_10_YEARS) - last_data_year
assert num_future_steps >= 10, "Need at least 10 years after last data year"


def fit_arima_forecast(y, order, steps):
    if ARIMA is None or len(y) < 5:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = ARIMA(y.astype(float), order=order)
            fit = model.fit()
            return np.asarray(fit.forecast(steps=steps), dtype=float)
        except Exception:
            return None


def fit_arima_val_test(y_train, order, steps_val, steps_test):
    if ARIMA is None or len(y_train) < 5:
        return None, None, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = ARIMA(y_train.astype(float), order=order)
            fit = model.fit()
            val_f = fit.forecast(steps=steps_val)
            full = fit.forecast(steps=steps_val + steps_test)
            return fit, np.asarray(val_f, dtype=float), np.asarray(full[-steps_test:], dtype=float)
        except Exception:
            return None, None, None


def select_order_and_forecast_future(country):
    y_train_full = train_df.loc[train_df["Country"] == country, train_years].values.flatten()
    y_train_full = np.nan_to_num(
        pd.to_numeric(y_train_full, errors="coerce"), nan=np.nanmean(y_train_full)
    )
    y_val = np.asarray(
        val_df.loc[val_df["Country"] == country, val_years].values.flatten(), dtype=float
    )
    y_test = np.asarray(
        test_df.loc[test_df["Country"] == country, test_years].values.flatten(), dtype=float
    )
    # Full history 1950–last_data_year (for OFR chain and for final forecast input when capped)
    y_history = np.concatenate([
        train_df.loc[train_df["Country"] == country, train_years].values.flatten(),
        val_df.loc[val_df["Country"] == country, val_years].values.flatten(),
        test_df.loc[test_df["Country"] == country, test_years].values.flatten(),
    ])
    y_history = np.nan_to_num(pd.to_numeric(y_history, errors="coerce"), nan=np.nanmean(y_history))
    y_history = np.asarray(y_history, dtype=float)

    if TRAIN_CAP_YEARS is not None and len(y_train_full) > TRAIN_CAP_YEARS:
        y_train_short = np.asarray(y_train_full[-TRAIN_CAP_YEARS:], dtype=float)
        best_val_short = np.inf
        for order in ORDERS_BY_SIMPLICITY:
            _, vf, _ = fit_arima_val_test(y_train_short, order, len(y_val), len(y_test))
            if vf is not None:
                mae = mean_absolute_error(y_val, vf)
                if mae < best_val_short:
                    best_val_short = mae
        best_val_full = np.inf
        for order in ORDERS_BY_SIMPLICITY:
            _, vf, _ = fit_arima_val_test(y_train_full, order, len(y_val), len(y_test))
            if vf is not None:
                mae = mean_absolute_error(y_val, vf)
                if mae < best_val_full:
                    best_val_full = mae
        if best_val_short <= best_val_full * (1 + VAL_MAE_TIE_TOL):
            y_train = y_train_short
        else:
            y_train = np.asarray(y_train_full, dtype=float)
    else:
        y_train = np.asarray(y_train_full, dtype=float)

    # Capped series for fitting the final model (same as forecast_agent)
    y_fit = y_history
    if TRAIN_CAP_YEARS is not None and len(y_fit) > TRAIN_CAP_YEARS:
        y_fit = np.asarray(y_fit[-TRAIN_CAP_YEARS:], dtype=float)

    # Order selection on train/val
    best_mae = np.inf
    chosen_order = None
    for order in ORDERS_BY_SIMPLICITY:
        _, vf, _ = fit_arima_val_test(y_train, order, len(y_val), len(y_test))
        if vf is not None:
            mae = mean_absolute_error(y_val, vf)
            if mae < best_mae:
                best_mae = mae
                chosen_order = order
    if chosen_order is None:
        chosen_order = (0, 1, 0)

    future_catch = fit_arima_forecast(y_fit, chosen_order, num_future_steps)
    if future_catch is None:
        last = float(y_fit[-1]) if len(y_fit) else 0.0
        future_catch = np.full(num_future_steps, last)

    return y_history, future_catch


def ofr_inflation_from_catch_series(catch_series, years):
    catch = np.asarray(catch_series, dtype=float)
    initial_catch = None
    for c in catch:
        if c is not None and not np.isnan(c) and c > 0:
            initial_catch = float(c)
            break
    if initial_catch is None or initial_catch == 0:
        ofr = np.full(len(catch), np.nan)
    else:
        ofr = np.where(
            np.isnan(catch) | (catch == 0), np.nan, catch / initial_catch * 100
        )

    ofr_change = np.full(len(catch), np.nan)
    for i in range(1, len(ofr)):
        if not np.isnan(ofr[i - 1]) and ofr[i - 1] != 0 and not np.isnan(ofr[i]):
            ofr_change[i] = (ofr[i] - ofr[i - 1]) / ofr[i - 1] * 100

    price = np.full(len(catch), np.nan)
    price[0] = PRICE_START
    for i in range(1, len(catch)):
        if np.isnan(ofr_change[i]):
            price[i] = price[i - 1]
        else:
            price[i] = price[i - 1] * (1 + BETA * (ofr_change[i] / 100))
        price[i] = max(0.0, price[i])

    inflation = np.full(len(catch), np.nan)
    for i in range(1, len(catch)):
        if not np.isnan(price[i - 1]) and price[i - 1] != 0 and not np.isnan(price[i]):
            inflation[i] = (price[i] - price[i - 1]) / price[i - 1] * 100

    return [
        (int(years[i]), ofr_change[i] if not np.isnan(ofr_change[i]) else None,
         inflation[i] if not np.isnan(inflation[i]) else None)
        for i in range(len(years))
    ]


history_years = list(map(int, train_years + val_years + test_years))
future_years_list = list(range(last_data_year + 1, last_data_year + 1 + num_future_steps))

rows_5 = []
rows_10 = []

for country in train_df["Country"]:
    y_history, future_catch = select_order_and_forecast_future(country)
    full_catch = np.concatenate([y_history, future_catch])
    full_years = history_years + future_years_list

    computed = ofr_inflation_from_catch_series(full_catch, full_years)
    by_year = {y: (o, i) for y, o, i in computed}

    for y in NEXT_5_YEARS:
        if y in by_year:
            o, i = by_year[y]
            rows_5.append({"Country": country, "Year": y, "OFR_change": o, "Inflation_pct": i})

    for y in NEXT_10_YEARS:
        if y in by_year:
            o, i = by_year[y]
            rows_10.append({"Country": country, "Year": y, "OFR_change": o, "Inflation_pct": i})

out_5 = pd.DataFrame(rows_5)
out_10 = pd.DataFrame(rows_10)
out_5 = out_5[["Country", "Year", "OFR_change", "Inflation_pct"]]
out_10 = out_10[["Country", "Year", "OFR_change", "Inflation_pct"]]
out_5.to_csv("forecast_next5years.csv", index=False)
out_10.to_csv("forecast_next10years.csv", index=False)
print("Current year:", CURRENT_YEAR)
print("Next 5 years:", NEXT_5_YEARS)
print("Next 10 years:", NEXT_10_YEARS)
print("forecast_next5years.csv  -> Country, Year, OFR_change, Inflation_pct")
print("forecast_next10years.csv -> Country, Year, OFR_change, Inflation_pct")
