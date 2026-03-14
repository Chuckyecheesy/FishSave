"""
Run neon_schema.sql against Neon PostgreSQL.
Requires: pip install psycopg2-binary python-dotenv
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

try:
    import psycopg2
except ImportError:
    raise SystemExit("Install psycopg2-binary: pip install psycopg2-binary")

schema_path = Path(__file__).parent / "neon_schema.sql"
sql = schema_path.read_text()

conn = psycopg2.connect(url)
conn.autocommit = True
try:
    with conn.cursor() as cur:
        cur.execute(sql)
    print("Neon schema applied: forecast_metrics, risk_score_intervals, country_risk_category")
finally:
    conn.close()
