"""
Load forecast_next5years.csv and forecast_next10years.csv into Neon table forecast_metrics.
Run after: python run_neon_schema.py
Requires: pip install psycopg2-binary python-dotenv pandas
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

load_dotenv()
url = os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL not set in .env")

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

def load_horizon(csv_path, horizon):
    df = pd.read_csv(csv_path)
    df["OFR_change"] = pd.to_numeric(df["OFR_change"], errors="coerce")
    df["Inflation_pct"] = pd.to_numeric(df["Inflation_pct"], errors="coerce")
    df["horizon"] = horizon
    return df[["Country", "Year", "OFR_change", "Inflation_pct", "horizon"]]

base = Path(__file__).parent
df5 = load_horizon(base / "forecast_next5years.csv", "5y")
df10 = load_horizon(base / "forecast_next10years.csv", "10y")
df = pd.concat([df5, df10], ignore_index=True)
df = df.rename(columns={"Country": "country", "Year": "year", "OFR_change": "ofr_change", "Inflation_pct": "inflation_pct"})

rows = [
    (row["country"], int(row["year"]), float(row["ofr_change"]) if pd.notna(row["ofr_change"]) else None, float(row["inflation_pct"]) if pd.notna(row["inflation_pct"]) else None, row["horizon"])
    for _, row in df.iterrows()
]

conn = psycopg2.connect(url)
try:
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO forecast_metrics (country, year, ofr_change, inflation_pct, horizon)
            VALUES %s
            ON CONFLICT (country, year, horizon) DO UPDATE SET
              ofr_change = EXCLUDED.ofr_change,
              inflation_pct = EXCLUDED.inflation_pct
            """,
            rows,
        )
    conn.commit()
    print(f"Loaded {len(rows)} rows into Neon forecast_metrics (5y + 10y)")
finally:
    conn.close()
