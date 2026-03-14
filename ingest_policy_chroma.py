"""
Scrape policy websites (FAO, OECD), embed with Cohere, and store in ChromaDB.
Then you can query and use explain_why_reduces_overfishing.py to get an explanation.

Sources (scraped):
  - FAO IPOA-CAP and IUU: https://www.fao.org/4/y3274e/y3274e0f.htm
  - OECD Managing fish stocks sustainably (PDF)
  - OECD Encouraging policy change (HTML; may 403)

Requires: pip install chromadb cohere python-dotenv requests beautifulsoup4 pypdf

Uses COHERE_API_KEY from .env. Creates persistent ChromaDB at ./chroma_policy_db.

Run: python ingest_policy_chroma.py
      python ingest_policy_chroma.py --static   # use policy_chunks.py only (no scrape)
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

load_dotenv()

COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
if not COHERE_API_KEY:
    raise SystemExit("COHERE_API_KEY not set in .env")

import chromadb
import cohere

EMBED_MODEL = "embed-multilingual-v3.0"
BATCH_SIZE = 96
CHROMA_PATH = Path(__file__).parent / "chroma_policy_db"
COLLECTION_NAME = "overfishing_policy_actions"


def get_chunks(use_scraper=True):
    if use_scraper:
        from scrape_policy_sources import scrape_all
        return scrape_all()
    from policy_chunks import get_all_chunks
    return get_all_chunks()


def main():
    use_scraper = "--static" not in sys.argv
    chunks = get_chunks(use_scraper=use_scraper)
    if not chunks:
        raise SystemExit("No policy chunks. Run without --static to scrape, or add data to policy_chunks.py.")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Implementation actions for policy to reduce overfishing (FAO, OECD)"},
    )

    co = cohere.Client(api_key=COHERE_API_KEY)

    documents = [c["content"] for c in chunks]
    metadatas = [{"source": c["source"], "url": c["url"], "topic": c["topic"]} for c in chunks]
    ids = [f"policy_{i}" for i in range(len(chunks))]

    all_embeddings = []
    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        out = co.embed(texts=batch, model=EMBED_MODEL, input_type="search_document")
        all_embeddings.extend(out.embeddings)
        print(f"  Embedded {min(i + BATCH_SIZE, len(documents))}/{len(documents)}")

    collection.add(
        ids=ids,
        embeddings=all_embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    print(f"ChromaDB updated: {len(chunks)} chunks in '{COLLECTION_NAME}' at {CHROMA_PATH}")


if __name__ == "__main__":
    main()
