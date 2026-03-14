"""
Risk-based recommendation: use ChromaDB policy embeddings + Gemini to generate text.

Framing:
  - Low risk   → No recommendation (no text generation).
  - Medium risk → ChromaDB retrieval: top 3 most impactful implementation actions → Gemini generates recommendation.
  - High risk  → ChromaDB retrieval: all relevant implementation actions → Gemini generates full recommendations.

Requires: pip install chromadb cohere google-generativeai python-dotenv pandas

Uses: COHERE_API_KEY (for embedding the query), GEMINI_API_KEY (for text generation) from .env.
Risk data: risk_score_with_category.csv (risk_category_pred = 5y band; 10y from risk_score_10y).
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None

load_dotenv()

ROOT = Path(__file__).parent
RISK_CSV = ROOT / "risk_score_with_category.csv"
CHROMA_PATH = ROOT / "chroma_policy_db"
COLLECTION_NAME = "overfishing_policy_actions"
EMBED_MODEL = "embed-multilingual-v3.0"
# Optional fallback Cohere embedding model (e.g. "deep-v3") used when the
# primary model returns quota / rate-limit errors (HTTP 429, credit issues).
COHERE_FALLBACK_EMBED_MODEL = os.environ.get("COHERE_FALLBACK_EMBED_MODEL", "").strip()

# ChromaDB retrieval: medium = top 3, high = top 15 (all impactful)
TOP_K_MEDIUM = 3
TOP_K_HIGH = 15

# Gemini models: 2.0 available on new projects; 1.5 may 404
GEMINI_MODELS = ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro")


def _score_to_band(s):
    if s is None or (isinstance(s, float) and (s != s or s < 0)):
        return "medium"
    s = float(s)
    if s < 0.45:
        return "low"
    if s < 0.55:
        return "medium"
    return "high"


def load_risk_bands():
    """Load country -> (risk_5y, risk_10y) from CSV."""
    import pandas as pd
    if not RISK_CSV.exists():
        return {}
    df = pd.read_csv(RISK_CSV)
    out = {}
    for _, row in df.iterrows():
        country = row["Country"]
        risk_5y = (row.get("risk_category_pred") or "").strip().lower() or _score_to_band(row.get("risk_score_5y"))
        risk_10y = _score_to_band(row.get("risk_score_10y"))
        if isinstance(risk_5y, str) and risk_5y not in ("low", "medium", "high"):
            risk_5y = _score_to_band(row.get("risk_score_5y"))
        out[country] = {"5y": risk_5y, "10y": risk_10y}
    return out


def get_risk_band(country, horizon="5y", risk_bands=None):
    """Return 'low' | 'medium' | 'high' for country and horizon."""
    if risk_bands is None:
        risk_bands = load_risk_bands()
    rec = risk_bands.get(country)
    if not rec:
        return "medium"
    return rec.get(horizon, "medium")


def retrieve_policy_chunks(query_embedding, top_k):
    """Return list of document strings from ChromaDB."""
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, 50),
        include=["documents", "metadatas"],
    )
    docs = results["documents"][0] if results["documents"] else []
    return docs


def embed_query(co, text):
    """Cohere embed for query with optional fallback model on quota errors."""
    try:
        out = co.embed(
            texts=[text],
            model=EMBED_MODEL,
            input_type="search_query",
        )
        return out.embeddings[0]
    except Exception as e:
        msg = str(e).lower()
        # Fallback only for obvious quota / credit / rate-limit style errors.
        if (
            "429" in msg
            or "rate limit" in msg
            or "quota" in msg
            or "credit" in msg
        ) and COHERE_FALLBACK_EMBED_MODEL:
            out = co.embed(
                texts=[text],
                model=COHERE_FALLBACK_EMBED_MODEL,
                input_type="search_query",
            )
            return out.embeddings[0]
        raise


def generate_recommendation_gemini(context_chunks, country, risk_band, horizon, top_n=None):
    """Use Gemini to generate recommendation text from policy chunks. Tries multiple models if one fails (quota/404)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "[Set GEMINI_API_KEY in .env]"
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except Exception as e:
        return f"[Gemini unavailable: {e}]"

    context = "\n\n".join([f"[{i+1}] {c}" for i, c in enumerate(context_chunks)])
    if top_n:
        prompt = f"""You are an expert in fisheries policy. For the country "{country}" (overfishing risk: {risk_band}, horizon: {horizon}), provide exactly the top {top_n} most impactful implementation actions to reduce overfishing. Use ONLY the following policy excerpts. Write in clear, actionable bullets. Do not add general advice beyond the excerpts.

Policy excerpts:
{context}

Top {top_n} impactful implementation actions for {country}:"""
    else:
        prompt = f"""You are an expert in fisheries policy. For the country "{country}" (overfishing risk: {risk_band}, horizon: {horizon}), provide implementation recommendations to reduce overfishing. Use the following policy excerpts. Write in clear, actionable sections (e.g. monitoring, capacity control, subsidies, enforcement). Do not add general advice beyond the excerpts.

Policy excerpts:
{context}

Implementation recommendations for {country}:"""

    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            err = str(e).lower()
            if "404" in err or "not found" in err or "quota" in err or "429" in err:
                continue
            return f"[Gemini error: {e}]"
    return "[Gemini: all models failed (try again later or check quota at https://ai.google.dev/gemini-api/docs/rate-limits)]"


def get_recommendation(country, horizon="5y"):
    """
    Main entry: return (risk_band, recommendation_text).
    - Low: recommendation_text is None or a short 'No recommendation' message.
    - Medium: top 3 from ChromaDB → Gemini.
    - High: top 15 from ChromaDB → Gemini.
    """
    risk_bands = load_risk_bands()
    band = get_risk_band(country, horizon=horizon, risk_bands=risk_bands)

    if band == "low":
        return band, None  # No recommendation

    co_key = os.environ.get("COHERE_API_KEY")
    if not co_key:
        return band, "[Set COHERE_API_KEY to retrieve policy actions.]"

    import cohere
    co = cohere.Client(api_key=co_key)
    query_text = "policy implementation actions to reduce overfishing and manage fishing capacity"
    q_emb = embed_query(co, query_text)

    if band == "medium":
        chunks = retrieve_policy_chunks(q_emb, TOP_K_MEDIUM)
        if not chunks:
            return band, "[No policy chunks in ChromaDB. Run ingest_policy_chroma.py]"
        text = generate_recommendation_gemini(chunks, country, band, horizon, top_n=TOP_K_MEDIUM)
        return band, text

    # high
    chunks = retrieve_policy_chunks(q_emb, TOP_K_HIGH)
    if not chunks:
        return band, "[No policy chunks in ChromaDB. Run ingest_policy_chroma.py]"
    text = generate_recommendation_gemini(chunks, country, band, horizon, top_n=None)
    return band, text


def main():
    if len(sys.argv) < 2:
        print("Usage: python recommend_by_risk.py <Country> [horizon]")
        print("  horizon: 5y (default) or 10y")
        print("Example: python recommend_by_risk.py Austria 5y")
        sys.exit(1)

    country = sys.argv[1]
    horizon = (sys.argv[2] if len(sys.argv) > 2 else "5y").strip().lower()
    if horizon not in ("5y", "10y"):
        horizon = "5y"

    band, recommendation = get_recommendation(country, horizon=horizon)

    print(f"Country: {country}")
    print(f"Horizon: {horizon}")
    print(f"Risk: {band}")
    print()
    if band == "low":
        print("No recommendation (low risk).")
    else:
        print("Recommendation:")
        print("-" * 40)
        print(recommendation or "")


if __name__ == "__main__":
    main()
