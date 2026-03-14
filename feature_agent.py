#!/usr/bin/env python3
"""Feature Engineering Agent for Overfishing Hackathon Project.

This script:
1) Aggregates the raw dataset so each country appears once (summing across species/location).
2) Computes Overfishing Risk (OFR) per country using the first available catch as baseline.
3) Computes year-on-year OFR change and a proxy PriceIndex using a beta sensitivity factor.
4) Saves the resulting wide table as `country_features.csv`.

Output columns:
  Country, 1950...2018, OFR, OFR_change, PriceIndex

Usage:
  python feature_agent.py --input FishStats2018.csv --output country_features.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd


def _year_columns(start: int = 1950, end: int = 2018) -> List[str]:
    return [str(y) for y in range(start, end + 1)]


def _first_nonzero(series: pd.Series) -> Optional[float]:
    """Return first non-null, non-zero value in a series, or None if none exists."""
    s = series.dropna()
    s = s[s != 0]
    if s.empty:
        return None
    return float(s.iloc[0])


def compute_country_features(
    df: pd.DataFrame,
    year_columns: List[str],
    beta: float = 0.5,
    price_index_start: float = 100.0,
) -> pd.DataFrame:
    """Aggregate countries and compute OFR, OFR_change, and PriceIndex."""

    # Aggregate duplicate countries (sum across year columns)
    agg = df.groupby("Country")[year_columns].sum(min_count=1).reset_index()

    # Ensure numeric types for year columns
    agg[year_columns] = agg[year_columns].apply(pd.to_numeric, errors="coerce")

    # Compute feature columns per country
    ofr_values = []
    ofr_change_values = []
    price_index_values = []

    for _, row in agg.iterrows():
        years = row[year_columns].astype(float)

        # Initial catch is the first non-zero/non-null yearly catch
        initial_catch = _first_nonzero(years)

        # OFR series (percent of initial catch)
        if initial_catch is None or initial_catch == 0:
            ofr_series = pd.Series([np.nan] * len(years), index=years.index)
        else:
            ofr_series = years / initial_catch * 100

        # Year-on-year OFR change (%)
        # Avoid implicit fill_method future warning by specifying None.
        ofr_change_series = ofr_series.pct_change(fill_method=None) * 100

        # Proxy PriceIndex (iterative)
        price_index = price_index_start
        price_index_series = []
        for change in ofr_change_series:
            if pd.isna(change):
                price_index_series.append(price_index)
            else:
                price_index = price_index * (1 + beta * (change / 100))
                price_index_series.append(price_index)

        # Take the most recent year's metrics (2018)
        ofr_values.append(ofr_series.iloc[-1] if len(ofr_series) else np.nan)
        ofr_change_values.append(ofr_change_series.iloc[-1] if len(ofr_change_series) else np.nan)
        price_index_values.append(price_index_series[-1] if len(price_index_series) else np.nan)

    agg["OFR"] = ofr_values
    agg["OFR_change"] = ofr_change_values
    agg["PriceIndex"] = price_index_values

    return agg


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature Engineering Agent for Overfishing Dataset")
    parser.add_argument(
        "--input",
        default="FishStats2018.csv",
        help="Path to the raw FishStats2018.csv file.",
    )
    parser.add_argument(
        "--output",
        default="country_features.csv",
        help="Output CSV path (default: country_features.csv).",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=0.5,
        help="Sensitivity factor for Proxy PriceIndex (default: 0.5).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=1950,
        help="Start year for aggregation (default: 1950).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2018,
        help="End year for aggregation (default: 2018).",
    )

    args = parser.parse_args()

    df = pd.read_csv(args.input)

    year_cols = _year_columns(args.start_year, args.end_year)
    missing = [c for c in year_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected year columns in input CSV: {missing}")

    features = compute_country_features(df, year_cols, beta=args.beta)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(out_path, index=False)

    print(f"Feature engineering complete. Saved as '{out_path}'.")


if __name__ == "__main__":
    main()
