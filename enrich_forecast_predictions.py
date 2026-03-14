"""
Enrich forecast_predictions.csv with OFR, OFR_change, PriceIndex, and Inflation.
- OFR = (catch / initial_catch) * 100, where catch = Actual if present else Forecast.
- OFR_change = year-on-year % change in OFR.
- PriceIndex = 100 * product(1 + beta * OFR_change/100) with beta=0.5.
- Inflation_pct = (PriceIndex_t - PriceIndex_{t-1}) / PriceIndex_{t-1} * 100.
"""
import pandas as pd
import numpy as np

BETA = 0.5
PRICE_START = 100.0

df = pd.read_csv("forecast_predictions.csv")
df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
df["Actual"] = pd.to_numeric(df["Actual"], errors="coerce")
df["Forecast"] = pd.to_numeric(df["Forecast"], errors="coerce")
# Catch: use Actual when available, else Forecast
df["Catch"] = df["Actual"].fillna(df["Forecast"])
df = df.sort_values(["Country", "Year"]).reset_index(drop=True)

rows = []
for country, grp in df.groupby("Country", sort=False):
    grp = grp.sort_values("Year")
    catch = grp["Catch"].values.astype(float)
    years = grp["Year"].values

    # Initial catch: first non-zero catch in the series
    initial_catch = None
    for c in catch:
        if c is not None and not np.isnan(c) and c > 0:
            initial_catch = float(c)
            break
    if initial_catch is None or initial_catch == 0:
        ofr = np.full(len(catch), np.nan)
    else:
        ofr = np.where(np.isnan(catch) | (catch == 0), np.nan, catch / initial_catch * 100)

    # Year-on-year OFR change (%)
    ofr_change = np.full(len(catch), np.nan)
    for i in range(1, len(ofr)):
        if not np.isnan(ofr[i - 1]) and ofr[i - 1] != 0 and not np.isnan(ofr[i]):
            ofr_change[i] = (ofr[i] - ofr[i - 1]) / ofr[i - 1] * 100

    # PriceIndex (iterative)
    price = np.full(len(catch), np.nan)
    price[0] = PRICE_START
    for i in range(1, len(catch)):
        if np.isnan(ofr_change[i]):
            price[i] = price[i - 1]
        else:
            price[i] = price[i - 1] * (1 + BETA * (ofr_change[i] / 100))
        price[i] = max(0.0, price[i])

    # Inflation_pct = (PriceIndex_t - PriceIndex_{t-1}) / PriceIndex_{t-1} * 100
    inflation = np.full(len(catch), np.nan)
    for i in range(1, len(catch)):
        if not np.isnan(price[i - 1]) and price[i - 1] != 0 and not np.isnan(price[i]):
            inflation[i] = (price[i] - price[i - 1]) / price[i - 1] * 100

    for i in range(len(grp)):
        rows.append({
            "Country": country,
            "Year": int(years[i]),
            "Actual": grp["Actual"].iloc[i],
            "Forecast": grp["Forecast"].iloc[i],
            "OFR": ofr[i] if not np.isnan(ofr[i]) else None,
            "OFR_change": ofr_change[i] if not np.isnan(ofr_change[i]) else None,
            "PriceIndex": price[i] if not np.isnan(price[i]) else None,
            "Inflation_pct": inflation[i] if not np.isnan(inflation[i]) else None,
        })

out = pd.DataFrame(rows)
# Reorder: Country, Year, Actual, Forecast, OFR, OFR_change, PriceIndex, Inflation_pct
out = out[["Country", "Year", "Actual", "Forecast", "OFR", "OFR_change", "PriceIndex", "Inflation_pct"]]
out.to_csv("forecast_predictions.csv", index=False)
print("Enriched forecast_predictions.csv with OFR, OFR_change, PriceIndex, Inflation_pct")
print("Columns:", list(out.columns))
