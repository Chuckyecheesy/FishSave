"""
Query ChromaDB for policy implementation actions to reduce overfishing.

Requires: pip install chromadb cohere python-dotenv
Run after: python ingest_policy_chroma.py

Usage:
  python query_policy_chroma.py "How to reduce overfishing with policy?"
  python query_policy_chroma.py "subsidies and fleet capacity" --limit 5
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

load_dotenv()

if not os.environ.get("COHERE_API_KEY"):
    raise SystemExit("COHERE_API_KEY not set in .env")

import chromadb
import cohere

CHROMA_PATH = Path(__file__).parent / "chroma_policy_db"
COLLECTION_NAME = "overfishing_policy_actions"
EMBED_MODEL = "embed-multilingual-v3.0"


def main():
    args = sys.argv[1:]
    limit = 5
    if "--limit" in args:
        idx = args.index("--limit")
        limit = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    query = " ".join(args) if args else "What are measurable policy actions to reduce overfishing?"

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)

    co = cohere.Client(api_key=os.environ["COHERE_API_KEY"])
    q_emb = co.embed(
        texts=[query],
        model=EMBED_MODEL,
        input_type="search_query",
    ).embeddings[0]

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )

    print(f"Query: {query}\n")
    for i, (doc, meta, dist) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ),
        1,
    ):
        print(f"{i}. [{meta.get('source', '')}] {meta.get('topic', '')} (distance: {dist:.4f})")
        print(f"   {doc[:220]}{'...' if len(doc) > 220 else ''}\n")


if __name__ == "__main__":
    main()
