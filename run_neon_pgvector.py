"""
Run neon_pgvector.sql against Neon PostgreSQL (pgvector extension + context_embeddings table).
Requires: pip install psycopg2-binary python-dotenv
Run after: python run_neon_schema.py
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

schema_path = Path(__file__).parent / "neon_pgvector.sql"
sql = schema_path.read_text()

conn = psycopg2.connect(url)
conn.autocommit = True
try:
    with conn.cursor() as cur:
        cur.execute(sql)
    print("Neon pgvector applied: vector extension, context_embeddings table, HNSW index")
finally:
    conn.close()
