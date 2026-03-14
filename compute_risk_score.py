"""
Compute risk score (inflation due to overfishing) for next 5 and next 10 years per country.
Uses slope and sum of Inflation_pct and OFR_change from forecast_next5years.csv and
forecast_next10years.csv. Saves risk_score.csv with Country, risk_score_5y, risk_score_10y
and optional component columns.
"""
import pandas as pd
import numpy as np


def safe_slope(years, values):
    """Linear regression slope; returns 0 if not enough valid points."""
    mask = np.isfinite(values) & ~np.isnan(values)
    x = np.asarray(years, dtype=float)[mask]
    y = np.asarray(values, dtype=float)[mask]
    if len(x) < 2:
        return 0.0
    x = x - x.min()
    return np.polyfit(x, y, 1)[0]


def safe_sum(values):
    """Sum of finite values; NaN treated as 0."""
    a = np.asarray(values, dtype=float)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return float(np.sum(a))


def min_max_norm(series):
    """Normalize to [0, 1]; constant series -> 0.5."""
    s = pd.Series(series)
    mn, mx = s.min(), s.max()
    if mx == mn or np.isnan(mx) or np.isnan(mn):
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


def compute_risk(df):
    """Compute slope and sum of OFR_change and Inflation_pct per country."""
    df = df.copy()
    df["OFR_change"] = pd.to_numeric(df["OFR_change"], errors="coerce")
    df["Inflation_pct"] = pd.to_numeric(df["Inflation_pct"], errors="coerce")
    rows = []
    for country, grp in df.groupby("Country", sort=False):
        grp = grp.sort_values("Year")
        years = grp["Year"].values
        ofr = grp["OFR_change"].values
        inf = grp["Inflation_pct"].values
        rows.append({
            "Country": country,
            "slope_OFR_change": safe_slope(years, ofr),
            "slope_Inflation_pct": safe_slope(years, inf),
            "sum_OFR_change": safe_sum(ofr),
            "sum_Inflation_pct": safe_sum(inf),
        })
    return pd.DataFrame(rows)


def main():
    df5 = pd.read_csv("forecast_next5years.csv")
    df10 = pd.read_csv("forecast_next10years.csv")

    r5 = compute_risk(df5)
    r10 = compute_risk(df10)
    r5 = r5.rename(columns={
        "slope_OFR_change": "slope_OFR_change_5y",
        "slope_Inflation_pct": "slope_Inflation_pct_5y",
        "sum_OFR_change": "sum_OFR_change_5y",
        "sum_Inflation_pct": "sum_Inflation_pct_5y",
    })
    r10 = r10.rename(columns={
        "slope_OFR_change": "slope_OFR_change_10y",
        "slope_Inflation_pct": "slope_Inflation_pct_10y",
        "sum_OFR_change": "sum_OFR_change_10y",
        "sum_Inflation_pct": "sum_Inflation_pct_10y",
    })
    r10 = r10.drop(columns=["Country"])
    combined = pd.concat([r5[["Country"]], r5.drop(columns=["Country"]), r10], axis=1)

    # Normalize each component to [0,1] across countries, then average -> risk score
    comp_5 = [
        "slope_OFR_change_5y", "slope_Inflation_pct_5y",
        "sum_OFR_change_5y", "sum_Inflation_pct_5y",
    ]
    comp_10 = [
        "slope_OFR_change_10y", "slope_Inflation_pct_10y",
        "sum_OFR_change_10y", "sum_Inflation_pct_10y",
    ]
    n5 = combined[comp_5].apply(min_max_norm)
    n10 = combined[comp_10].apply(min_max_norm)
    combined["risk_score_5y"] = n5.mean(axis=1).round(6)
    combined["risk_score_10y"] = n10.mean(axis=1).round(6)

    # Output: Country, risk_score_5y, risk_score_10y, then optional components
    out_cols = ["Country", "risk_score_5y", "risk_score_10y"] + comp_5 + comp_10
    out = combined[out_cols]
    out.to_csv("risk_score.csv", index=False)
    print("Saved risk_score.csv")
    print("Columns:", list(out.columns))
    print("\nSample (first 5 countries):")
    print(out.head().to_string(index=False))


if __name__ == "__main__":
    main()
