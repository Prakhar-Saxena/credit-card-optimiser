import io
import re
import urllib.request

import pypdf
from ddgs import DDGS
from config import HEADERS

# URL path fragments that signal official documentation vs marketing pages
_DOC_KEYWORDS = [
    'terms', 'agreement', 'rpa', 'offer', 'rules',
    'supplement', 'conditions', 'rewards-program', 'cardmember',
]

# Country-code TLDs that indicate a non-US site — penalised in scoring
_NON_US_TLDS = [
    '.com.au', '.co.uk', '.ca', '.com.mx', '.co.in', '.com.sg',
    '.co.nz', '.com.hk', '.ie', '.co.za', '.com.br', '.com.ar',
]

# Path/locale segments that indicate non-US content on otherwise .com domains
# e.g. amex.com/en-idc/ (India), amex.com/content/dam/amex/au/
_NON_US_PATH_SEGMENTS = [
    '/au/', '/en-au', '/en-gb', '/en-ca', '/en-in', '/en-idc',
    '/en-sg', '/en-hk', '/en-mx', '/en-ie', '/en-za', '/en-br',
    '/uk/', '/idc/', '/dam/amex/au', '/dam/amex/uk', '/dam/amex/ca',
]

# Substrings in the domain/path that indicate a US locale (bonus)
_US_SIGNALS = ['/us/', '/us-', 'unitedstates', '-us.', '/en-us', 'en_us']


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


def is_doc_url(url):
    """Return True if the URL looks like official documentation rather than a marketing page."""
    u = url.lower()
    return u.endswith('.pdf') or any(kw in u for kw in _DOC_KEYWORDS)


def score_doc_url(url):
    """
    Score a URL by how much it resembles official US documentation (higher = better).
    Bonuses: doc keywords, PDF extension, US locale signals.
    Penalties: country-code TLDs that indicate a non-US site.
    """
    u = url.lower()
    score = sum(kw in u for kw in _DOC_KEYWORDS)
    if u.endswith('.pdf'):
        score += 3
    if any(sig in u for sig in _US_SIGNALS):
        score += 2
    if any(tld in u for tld in _NON_US_TLDS):
        score -= 5
    if any(seg in u for seg in _NON_US_PATH_SEGMENTS):
        score -= 5
    return score


def fetch_doc_text(url, max_chars=4000):
    """
    Fetch a document URL and return plain text.
    Handles both HTML pages and PDFs transparently.
    """
    if _is_pdf(url):
        return _fetch_pdf(url, max_chars)
    return fetch_page_text(url, max_chars)


def fetch_page_text(url, max_chars=4000):
    """Fetch an HTML URL and return stripped plain text, or None if unusable."""
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


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _is_pdf(url):
    u = url.lower()
    return u.endswith('.pdf') or '.pdf?' in u or '/pdf/' in u


def _fetch_pdf(url, max_chars=4000):
    """Fetch a PDF and extract its text with pypdf."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        reader = pypdf.PdfReader(io.BytesIO(data))
        pages_text = (page.extract_text() or "" for page in reader.pages)
        text = " ".join(pages_text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars] if len(text) >= 100 else None
    except Exception as e:
        print(f"    [PDF fetch failed: {e}]")
        return None
