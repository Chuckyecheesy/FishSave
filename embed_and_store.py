"""
Generate Cohere embeddings for context text and store them in Neon pgvector.

Run after:
  1. python run_neon_schema.py
  2. Apply neon_pgvector.sql (or run_neon_schema.py then run this with --migrate)
  3. Optionally load forecast_metrics and country_risk_category

Requires: pip install psycopg2-binary python-dotenv cohere

Uses COHERE_API_KEY and DATABASE_URL from .env.
Embedding model: embed-multilingual-v3.0 (1024 dimensions).
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not set in .env")
if not COHERE_API_KEY:
    raise SystemExit("COHERE_API_KEY not set in .env")

import psycopg2

# Cohere embed model: 1024 dimensions (must match neon_pgvector.sql vector(1024))
EMBED_MODEL = "embed-multilingual-v3.0"
BATCH_SIZE = 96  # Cohere embed batch limit


def _format_vector(embedding):
    """Format list of floats as pgvector literal."""
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


def run_pgvector_migration(conn):
    """Create pgvector extension and context_embeddings table if missing."""
    base = Path(__file__).parent
    sql_path = base / "neon_pgvector.sql"
    if not sql_path.exists():
        raise SystemExit("neon_pgvector.sql not found")
    sql = sql_path.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("Applied neon_pgvector.sql")


def fetch_texts_to_embed(conn):
    """
    Collect (source_type, source_id, content) from DB.
    Prefer context_meaning; otherwise build a short description for RAG.
    """
    rows = []
    with conn.cursor() as cur:
        # country_risk_category: one row per country
        cur.execute("""
            SELECT country, risk_score_5y, risk_score_10y, risk_5y, risk_10y, context_meaning
            FROM country_risk_category
        """)
        for r in cur.fetchall():
            country, s5, s10, band5, band10, ctx = r
            content = ctx if (ctx and str(ctx).strip()) else (
                f"Country: {country}. 5-year risk: {band5} (score {s5}). 10-year risk: {band10} (score {s10})."
            )
            rows.append(("country_risk_category", country, content))

        # risk_score_intervals: low/medium/high bands
        cur.execute("""
            SELECT band_name, context_meaning FROM risk_score_intervals ORDER BY sort_order
        """)
        for r in cur.fetchall():
            band, ctx = r
            if ctx and str(ctx).strip():
                rows.append(("risk_score_intervals", band, ctx))

        # forecast_metrics: optional context_meaning per (country, year, horizon)
        cur.execute("""
            SELECT country, year, horizon, context_meaning, ofr_change, inflation_pct
            FROM forecast_metrics
            LIMIT 2000
        """)
        for r in cur.fetchall():
            country, year, horizon, ctx, ofr, inf = r
            if ctx and str(ctx).strip():
                content = ctx
            else:
                content = (
                    f"Country: {country}, Year: {year}, Horizon: {horizon}. "
                    f"OFR change: {ofr}, Inflation %: {inf}."
                )
            source_id = f"{country}|{year}|{horizon}"
            rows.append(("forecast_metrics", source_id, content))
    return rows


def embed_batch(co, texts):
    """Call Cohere embed API for a list of texts. Returns list of lists (vectors)."""
    if not texts:
        return []
    out = co.embed(
        texts=texts,
        model=EMBED_MODEL,
        input_type="search_document",
    )
    return out.embeddings


def upsert_embeddings(conn, rows_with_embeddings):
    """Insert or update context_embeddings (source_type, source_id, content, embedding)."""
    with conn.cursor() as cur:
        for source_type, source_id, content, embedding in rows_with_embeddings:
            vec = _format_vector(embedding)
            # Escape single quotes in content for SQL
            content_esc = content.replace("'", "''")
            cur.execute("""
                INSERT INTO context_embeddings (source_type, source_id, content, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (source_type, source_id) DO UPDATE SET
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding,
                  created_at = NOW()
            """, (source_type, source_id, content_esc, vec))
    conn.commit()


def main():
    migrate_only = "--migrate" in sys.argv
    conn = psycopg2.connect(DATABASE_URL)
    try:
        run_pgvector_migration(conn)
        if migrate_only:
            print("Migration only (--migrate). Exiting.")
            return
    except Exception as e:
        conn.rollback()
        # If extension/table already exist, continue
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            raise

    import cohere
    co = cohere.Client(api_key=COHERE_API_KEY)

    rows = fetch_texts_to_embed(conn)
    if not rows:
        print("No rows to embed. Load country_risk_category and/or forecast_metrics first.")
        return
    print(f"Embedding {len(rows)} texts in batches of {BATCH_SIZE}...")

    all_with_embeddings = []
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        texts = [r[2] for r in batch]
        embeddings = embed_batch(co, texts)
        for (st, sid, content), emb in zip(batch, embeddings):
            all_with_embeddings.append((st, sid, content, emb))
        print(f"  Embedded {min(i + BATCH_SIZE, len(rows))}/{len(rows)}")

    upsert_embeddings(conn, all_with_embeddings)
    print(f"Done. Stored {len(all_with_embeddings)} embeddings in context_embeddings.")


if __name__ == "__main__":
    main()
