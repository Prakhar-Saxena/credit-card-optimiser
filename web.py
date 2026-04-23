import re
import urllib.request
from ddgs import DDGS
from config import HEADERS


def ddg_search(query, max_results=5):
    """
    Search DuckDuckGo via the ddgs package (handles bot detection internally).
    Returns (urls, snippets).
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        print(f"    [search error: {e}]")
        return [], []

    urls = [r["href"] for r in results]
    snippets = [r["body"] for r in results if r.get("body")]
    return urls, snippets


def fetch_page_text(url, max_chars=4000):
    """Fetch a URL and return stripped plain text, or None if unusable."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [fetch failed: {e}]")
        return None

    html = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    return text[:max_chars] if len(text) >= 200 else None
