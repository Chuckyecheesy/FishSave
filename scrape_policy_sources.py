"""
Scrape policy implementation content from FAO and OECD URLs, chunk it, and return
data ready for ChromaDB. Used by ingest_policy_chroma.py.

Sources:
  - FAO IPOA-CAP and IUU: https://www.fao.org/4/y3274e/y3274e0f.htm
  - OECD Managing fish stocks sustainably (PDF)
  - OECD Encouraging policy change (HTML; may 403)

Requires: pip install requests beautifulsoup4 pypdf
"""

import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Policy URLs to scrape
FAO_IPOA_URL = "https://www.fao.org/4/y3274e/y3274e0f.htm"
OECD_PDF_URL = "https://www.oecd.org/content/dam/oecd/en/publications/reports/2023/01/managing-fish-stocks-sustainably_552926af/60686388-en.pdf"
OECD_POLICY_CHANGE_URL = "https://www.oecd-ilibrary.org/agriculture-and-food/encouraging-policy-change-for-sustainable-and-resilient-fisheries_31f15060-en"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

# Min/max chunk size (chars) for embedding
MIN_CHUNK_CHARS = 150
MAX_CHUNK_CHARS = 800


def _clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def scrape_fao(url=FAO_IPOA_URL):
    """Fetch FAO HTML and extract main text; return list of (text, source, url, topic)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return [{"content": f"[Scrape failed: {e}]", "source": "FAO", "url": url, "topic": "error"}]

    soup = BeautifulSoup(r.text, "html.parser")
    # Remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()
    body = soup.find("body") or soup
    text = body.get_text(separator="\n")
    lines = [_clean_text(line) for line in text.splitlines() if _clean_text(line)]
    # Drop very short lines (nav/numbers)
    lines = [ln for ln in lines if len(ln) > 40]
    # Chunk by grouping lines
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        if current_len + len(line) + 1 > MAX_CHUNK_CHARS and current:
            content = " ".join(current)
            if len(content) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "content": content,
                    "source": "FAO",
                    "url": url,
                    "topic": "policy_implementation",
                })
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        content = " ".join(current)
        if len(content) >= MIN_CHUNK_CHARS:
            chunks.append({
                "content": content,
                "source": "FAO",
                "url": url,
                "topic": "policy_implementation",
            })
    return chunks


def scrape_oecd_pdf(url=OECD_PDF_URL):
    """Fetch OECD PDF and extract text; return list of chunks."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=45, stream=True)
        r.raise_for_status()
    except Exception as e:
        return [{"content": f"[PDF fetch failed: {e}]", "source": "OECD", "url": url, "topic": "error"}]

    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(r.content))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        full_text = "\n".join(parts)
    except Exception as e:
        return [{"content": f"[PDF parse failed: {e}]", "source": "OECD", "url": url, "topic": "error"}]

    full_text = _clean_text(full_text.replace("\n", " "))
    # Split into sentences/paragraphs (rough: by . )
    segments = re.split(r"(?<=[.])\s+", full_text)
    segments = [s.strip() for s in segments if len(s.strip()) > 30]
    chunks = []
    current = []
    current_len = 0
    for seg in segments:
        if current_len + len(seg) + 1 > MAX_CHUNK_CHARS and current:
            content = " ".join(current)
            if len(content) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "content": content,
                    "source": "OECD",
                    "url": url,
                    "topic": "managing_fish_stocks",
                })
            current = []
            current_len = 0
        current.append(seg)
        current_len += len(seg) + 1
    if current:
        content = " ".join(current)
        if len(content) >= MIN_CHUNK_CHARS:
            chunks.append({
                "content": content,
                "source": "OECD",
                "url": url,
                "topic": "managing_fish_stocks",
            })
    return chunks


def scrape_oecd_html(url=OECD_POLICY_CHANGE_URL):
    """Fetch OECD iLibrary HTML if accessible."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    body = soup.find("body") or soup
    text = body.get_text(separator="\n")
    lines = [_clean_text(line) for line in text.splitlines() if _clean_text(line) and len(_clean_text(line)) > 50]
    if not lines:
        return []
    content = " ".join(lines[:50])  # first 50 lines
    if len(content) < MIN_CHUNK_CHARS:
        return []
    return [{
        "content": content[:3000],
        "source": "OECD",
        "url": url,
        "topic": "policy_change",
    }]


def scrape_all():
    """Scrape all policy sources and return combined list of chunk dicts."""
    out = []
    print("Scraping FAO IPOA-CAP and IUU...")
    out.extend(scrape_fao())
    print(f"  -> {len([c for c in out if c['source'] == 'FAO'])} chunks")
    print("Scraping OECD Managing fish stocks (PDF)...")
    pdf_chunks = scrape_oecd_pdf()
    out.extend(pdf_chunks)
    print(f"  -> {len(pdf_chunks)} chunks")
    print("Scraping OECD Encouraging policy change...")
    html_chunks = scrape_oecd_html()
    out.extend(html_chunks)
    print(f"  -> {len(html_chunks)} chunks")
    return out


if __name__ == "__main__":
    chunks = scrape_all()
    print(f"\nTotal chunks: {len(chunks)}")
    for i, c in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i+1} ({c['source']}, {c['topic']}) ---")
        print(c["content"][:300] + "..." if len(c["content"]) > 300 else c["content"])
