"""
Example: semantic search over context_embeddings using Cohere + pgvector.

Requires: pip install psycopg2-binary python-dotenv cohere
Uses COHERE_API_KEY and DATABASE_URL from .env.

Usage:
  python query_embeddings.py "Which countries have high overfishing risk?"
  python query_embeddings.py "sustainable fishing 5 year" --limit 5
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
if not DATABASE_URL or not COHERE_API_KEY:
    raise SystemExit("Set DATABASE_URL and COHERE_API_KEY in .env")

import psycopg2
import cohere

EMBED_MODEL = "embed-multilingual-v3.0"


def embed_query(co, query: str):
    """Embed the search query (use input_type search_query for retrieval)."""
    out = co.embed(texts=[query], model=EMBED_MODEL, input_type="search_query")
    emb = out.embeddings[0]
    return "[" + ",".join(str(float(x)) for x in emb) + "]"


def main():
    args = sys.argv[1:]
    limit = 5
    if "--limit" in args:
        idx = args.index("--limit")
        limit = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    query = " ".join(args) if args else "overfishing risk by country"

    co = cohere.Client(api_key=COHERE_API_KEY)
    vec = embed_query(co, query)

    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        # Cosine distance: <=> ; ORDER BY embedding <=> query LIMIT k
        cur.execute("""
            SELECT source_type, source_id, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM context_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (vec, vec, limit))
        rows = cur.fetchall()

    print(f"Query: {query}\n")
    for i, (st, sid, content, sim) in enumerate(rows, 1):
        print(f"{i}. [{st}] {sid} (similarity: {sim:.4f})")
        print(f"   {content[:200]}{'...' if len(content) > 200 else ''}\n")


if __name__ == "__main__":
    main()
