"""
Load risk_score_with_category.csv into Neon table country_risk_category.
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

def score_to_band(s):
    if pd.isna(s):
        return "medium"
    s = float(s)
    if s < 0.45:
        return "low"
    if s < 0.55:
        return "medium"
    return "high"

csv_path = Path(__file__).parent / "risk_score_with_category.csv"
df = pd.read_csv(csv_path)
df["risk_10y"] = df["risk_score_10y"].apply(score_to_band)

conn = psycopg2.connect(url)
try:
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO country_risk_category (country, risk_score_5y, risk_score_10y, risk_5y, risk_10y)
            VALUES %s
            ON CONFLICT (country) DO UPDATE SET
              risk_score_5y = EXCLUDED.risk_score_5y,
              risk_score_10y = EXCLUDED.risk_score_10y,
              risk_5y = EXCLUDED.risk_5y,
              risk_10y = EXCLUDED.risk_10y,
              updated_at = NOW()
            """,
            [
                (
                    row["Country"],
                    float(row["risk_score_5y"]),
                    float(row["risk_score_10y"]),
                    row["risk_category_pred"],
                    row["risk_10y"],
                )
                for _, row in df.iterrows()
            ],
        )
    conn.commit()
    print(f"Loaded {len(df)} rows into Neon country_risk_category")
finally:
    conn.close()
