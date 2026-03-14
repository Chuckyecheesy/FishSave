"""
Tests for the policy implementation pipeline: scraper, chunks, ChromaDB ingest, and explain.

Run: python -m pytest test_policy_implementation.py -v
      or: python test_policy_implementation.py
"""

import os
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

REQUIRED_KEYS = {"content", "source", "url", "topic"}
CHROMA_PATH = ROOT / "chroma_policy_db"
COLLECTION_NAME = "overfishing_policy_actions"


def test_policy_chunks_structure():
    """Static policy chunks have required keys and non-empty content."""
    from policy_chunks import get_all_chunks

    chunks = get_all_chunks()
    assert len(chunks) >= 1, "policy_chunks should have at least one chunk"
    for c in chunks:
        assert set(c.keys()) >= REQUIRED_KEYS, f"Chunk missing keys: {c.keys()}"
        assert isinstance(c["content"], str) and len(c["content"].strip()) > 0
        assert c["source"] in ("FAO", "OECD")
        assert c["url"].startswith("http")


def test_scraper_returns_valid_chunks():
    """Scraper returns list of dicts with content, source, url, topic."""
    from scrape_policy_sources import scrape_fao, scrape_all

    # FAO scraper returns list of dicts with required keys
    fao_chunks = scrape_fao()
    assert isinstance(fao_chunks, list)
    for c in fao_chunks:
        assert set(c.keys()) >= REQUIRED_KEYS
        assert isinstance(c["content"], str)
        assert c["source"] == "FAO"
        assert "fao.org" in c["url"]

    # scrape_all returns combined list
    all_chunks = scrape_all()
    assert isinstance(all_chunks, list)
    assert len(all_chunks) >= len(fao_chunks)
    sources = {c["source"] for c in all_chunks}
    assert "FAO" in sources


def test_chroma_collection_has_documents():
    """If ChromaDB exists and was ingested, collection has documents and is queryable."""
    if not CHROMA_PATH.exists():
        return  # skip if ingest never run
    try:
        import chromadb
    except ImportError:
        return
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)
    n = collection.count()
    assert n >= 1, "ChromaDB collection should have at least one document after ingest"
    # Quick query (no embedding - just get a few)
    results = collection.get(limit=2, include=["documents", "metadatas"])
    assert len(results["ids"]) >= 1
    assert len(results["documents"]) >= 1
    assert "source" in results["metadatas"][0]


def test_explain_retrieves_from_chroma():
    """Explain script logic: query ChromaDB returns chunks that can be passed to LLM."""
    if not CHROMA_PATH.exists():
        return
    if not os.environ.get("COHERE_API_KEY"):
        return
    try:
        import chromadb
        import cohere
    except ImportError:
        return
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)
    co = cohere.Client(api_key=os.environ["COHERE_API_KEY"])
    q_emb = co.embed(
        texts=["policy to reduce overfishing"],
        model="embed-multilingual-v3.0",
        input_type="search_query",
    ).embeddings[0]
    results = collection.query(
        query_embeddings=[q_emb],
        n_results=3,
        include=["documents", "metadatas"],
    )
    assert len(results["documents"][0]) >= 1
    assert "overfishing" in results["documents"][0][0].lower() or "fishing" in results["documents"][0][0].lower()


def run_all():
    """Run tests and print results (no pytest required)."""
    tests = [
        ("policy_chunks structure", test_policy_chunks_structure),
        ("scraper returns valid chunks", test_scraper_returns_valid_chunks),
        ("ChromaDB collection has documents", test_chroma_collection_has_documents),
        ("explain retrieves from ChromaDB", test_explain_retrieves_from_chroma),
    ]
    passed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name} -> {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
