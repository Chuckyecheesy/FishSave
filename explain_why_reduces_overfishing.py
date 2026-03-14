"""
Query ChromaDB for policy implementation chunks, then use Cohere to write an
explanation of why these policies reduce overfishing.

Requires: pip install chromadb cohere python-dotenv
Run after: python ingest_policy_chroma.py

Usage:
  python explain_why_reduces_overfishing.py
  python explain_why_reduces_overfishing.py --limit 15
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
# Optional fallback embedding model (e.g. "deep-v3") for quota / 429 errors.
COHERE_FALLBACK_EMBED_MODEL = os.environ.get("COHERE_FALLBACK_EMBED_MODEL", "").strip()
QUERY = "policy implementation actions to reduce overfishing and manage fishing capacity"
DEFAULT_LIMIT = 12


def main():
    args = sys.argv[1:]
    limit = DEFAULT_LIMIT
    if "--limit" in args:
        idx = args.index("--limit")
        limit = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)

    co = cohere.Client(api_key=os.environ["COHERE_API_KEY"])
    try:
        q_emb = co.embed(
            texts=[QUERY],
            model=EMBED_MODEL,
            input_type="search_query",
        ).embeddings[0]
    except Exception as e:
        msg = str(e).lower()
        if (
            "429" in msg
            or "rate limit" in msg
            or "quota" in msg
            or "credit" in msg
        ) and COHERE_FALLBACK_EMBED_MODEL:
            q_emb = co.embed(
                texts=[QUERY],
                model=COHERE_FALLBACK_EMBED_MODEL,
                input_type="search_query",
            ).embeddings[0]
        else:
            raise

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=min(limit, 30),
        include=["documents", "metadatas"],
    )

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    if not docs:
        print("No policy chunks in ChromaDB. Run: python ingest_policy_chroma.py")
        return

    # Build context for the model
    numbered = []
    for i, (doc, meta) in enumerate(zip(docs, metadatas), 1):
        numbered.append(f"[{i}] (Source: {meta.get('source', '')}, URL: {meta.get('url', '')})\n{doc}")
    context = "\n\n---\n\n".join(numbered)

    prompt = f"""The following excerpts are from international policy documents (FAO and OECD) on fisheries management and reducing overfishing. Based only on these excerpts, write a clear, structured explanation of why these policy measures help reduce overfishing. Cover: (1) what the main types of measures are, (2) how they address overfishing (e.g. capacity, incentives, monitoring), and (3) why implementing them is expected to reduce overfishing. Use the document content to support your points. Keep the explanation concise but specific.

Policy excerpts:

{context}

Explanation of why these policies reduce overfishing:
"""

    # Cohere chat (use current model; command-r-plus was deprecated)
    try:
        response = co.chat(
            message=prompt,
            model="command-a-03-2025",
        )
        text = response.text
    except Exception as e1:
        try:
            response = co.chat(message=prompt, model="command")
            text = response.text
        except Exception as e2:
            print(f"Cohere API error: {e1}")
            return

    print("Retrieved", len(docs), "policy chunks from ChromaDB.\n")
    print("=" * 60)
    print("WHY THESE POLICIES REDUCE OVERFISHING")
    print("=" * 60)
    print(text.strip())
    print("\nSources: FAO and OECD policy documents (see URLs in ingested chunks).")


if __name__ == "__main__":
    main()
