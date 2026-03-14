"""
Create one graph per country: Year (x) vs OFR_change and Inflation_pct (y),
with legend and colour coding. Separate outputs for 5y and 10y forecasts.

Output:
  - graphs_5y/<Country>_5y.png  (from forecast_next5years.csv)
  - graphs_10y/<Country>_10y.png (from forecast_next10years.csv)

Requires: pip install pandas matplotlib
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re

ROOT = Path(__file__).parent
CSV_5Y = ROOT / "forecast_next5years.csv"
CSV_10Y = ROOT / "forecast_next10years.csv"
OUT_5Y = ROOT / "graphs_5y"
OUT_10Y = ROOT / "graphs_10y"


def safe_filename(name):
    """Make a safe filename from country name."""
    return re.sub(r'[^\w\s-]', '', name).strip().replace(" ", "_") or "Unknown"


def plot_country(df_sub, country, out_dir, horizon_label):
    """Plot Year vs OFR_change and Inflation_pct for one country; save to out_dir."""
    df_sub = df_sub.sort_values("Year")
    years = df_sub["Year"].values
    ofr = pd.to_numeric(df_sub["OFR_change"], errors="coerce").values
    inf = pd.to_numeric(df_sub["Inflation_pct"], errors="coerce").values

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(years, ofr, color="C0", marker="o", markersize=4, label="OFR_change", linewidth=1.5)
    ax.plot(years, inf, color="C1", marker="s", markersize=4, label="Inflation_pct", linewidth=1.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Value")
    ax.set_title(f"{country} — Forecast ({horizon_label})")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(years.min(), years.max())
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(country) + f"_{horizon_label.replace(' ', '')}.png"
    fig.savefig(out_dir / fname, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main():
    for csv_path, out_dir, label in [
        (CSV_5Y, OUT_5Y, "5y"),
        (CSV_10Y, OUT_10Y, "10y"),
    ]:
        if not csv_path.exists():
            print(f"Skip: {csv_path} not found")
            continue
        df = pd.read_csv(csv_path)
        countries = df["Country"].dropna().unique()
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Writing {len(countries)} graphs to {out_dir} ({label})...")
        for i, country in enumerate(countries):
            sub = df[df["Country"] == country]
            plot_country(sub, country, out_dir, label)
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(countries)}")
        print(f"  Done: {out_dir}")


if __name__ == "__main__":
    main()
