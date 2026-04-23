#!/usr/bin/env python3
"""
Credit card optimizer.

Modes:
  compare (default)  Full breakdown, ecosystem relationships, and combo recommendations.
  use                Pick the best card for a specific purchase to maximise rewards.

Usage:
  python search.py                          # compare all cards in cards.json
  python search.py use "groceries"
  python search.py use "dining at Nobu"
  python search.py use "flight on Delta"
"""

import argparse
import urllib.request
import urllib.parse
import json
import re
import sys
import os
from ddgs import DDGS

CARDS_FILE = os.path.join(os.path.dirname(__file__), "cards.json")
MODEL = "qwen2.5:3b"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def load_cards(path=CARDS_FILE):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list) or len(data) < 2:
        print(f"Error: {path} must be a JSON array with at least 2 card names.", file=sys.stderr)
        sys.exit(1)
    return [str(c) for c in data]


def ddg_search(query, max_results=5):
    """
    Search DuckDuckGo via the ddgs package (handles bot detection internally).
    Returns (urls, snippets) — both lists are parallel to the result set.
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


def resolve_issuer_domains(card_names):
    """
    Ask the model for each card's issuing bank domain.
    Returns a dict mapping card name -> domain string (or None).
    """
    names_block = "\n".join(f"- {n}" for n in card_names)
    prompt = f"""For each credit card below, return the website domain of the BANK or FINANCIAL INSTITUTION that issues the card — not the retail partner. For example:
- "Costco Anywhere Visa Card by Citi" → citi.com  (Citi is the issuing bank, not Costco)
- "Amazon Prime Rewards Visa Signature" → chase.com  (Chase issues it, not Amazon)
- "Chase Sapphire Reserve" → chase.com
- "American Express Platinum" → americanexpress.com

Return a JSON object where each key is the exact card name and the value is the issuing bank's domain. Return ONLY the JSON, no other text.

Cards:
{names_block}

JSON:"""

    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": True}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    parts = []
    with urllib.request.urlopen(req) as r:
        for line in r:
            chunk = json.loads(line)
            parts.append(chunk.get("response", ""))
            if chunk.get("done"):
                break
    raw = "".join(parts)

    # Accept both {"Card": "domain"} object and ["domain", ...] array
    domain_map = {}
    obj_match = re.search(r'\{.*\}', raw, re.DOTALL)
    arr_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if obj_match:
        try:
            domain_map = json.loads(obj_match.group())
        except json.JSONDecodeError:
            pass
    elif arr_match:
        try:
            arr = json.loads(arr_match.group())
            domain_map = dict(zip(card_names, arr))
        except (json.JSONDecodeError, TypeError):
            pass

    resolved = {}
    for name in card_names:
        domain = domain_map.get(name) or None
        if domain:
            domain = re.sub(r'^https?://', '', str(domain)).split('/')[0].strip()
        resolved[name] = domain
        print(f"  {name}: {domain or 'unknown — will search without site filter'}")

    return resolved


def gather_card_context(card_names, domain_map):
    """
    For each card, search DDG restricted to the issuer's domain, fetch the
    first working page, and fall back to unrestricted snippets if needed.
    Returns list of (name, text) tuples.
    """
    results = []
    for name in card_names:
        domain = domain_map.get(name)
        base_query = f"{name} credit card rewards benefits"
        site_query = f"site:{domain} {base_query}" if domain else base_query

        print(f"  [{name}]")
        print(f"    Searching: {site_query!r}")
        urls, snippets = ddg_search(site_query)

        # If site-scoped search returned nothing, fall back to open search
        if not urls and domain:
            print(f"    No results on {domain}, retrying without site filter...")
            urls, snippets = ddg_search(base_query)

        text = None
        for url in urls:
            print(f"    Fetching: {url}")
            text = fetch_page_text(url)
            if text:
                print(f"    OK — {len(text)} chars")
                break
            print(f"    Failed or JS-only, trying next...")

        if not text:
            if snippets:
                print(f"    Using search snippets as fallback")
                text = "\n".join(f"- {s}" for s in snippets)
            else:
                print(f"    No data retrieved")

        results.append((name, text or "[No data retrieved]"))

    return results


def build_card_context_block(card_contexts):
    return "\n\n".join(f"=== {name} ===\n{text}" for name, text in card_contexts)


def ask_ollama_stream(prompt):
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": True}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        for line in r:
            chunk = json.loads(line)
            print(chunk.get("response", ""), end="", flush=True)
            if chunk.get("done"):
                break
    print()


def run_compare(card_names, domain_map):
    cards_list = ", ".join(card_names)
    print(f"Cards: {cards_list}\n")
    print("Fetching card data...\n")

    card_contexts = gather_card_context(card_names, domain_map)

    print("\nSearching: card combination and synergy strategies...")
    _, synergy_snippets = ddg_search(" ".join(card_names) + " credit card points pooling transfer strategy")

    context = build_card_context_block(card_contexts)
    if synergy_snippets:
        context += "\n\n=== Combination & Ecosystem Strategies ===\n" + "\n".join(f"- {s}" for s in synergy_snippets)

    print(f"\nGathered data for {len(card_contexts)} cards. Asking model...\n")
    print("=" * 60)

    prompt = f"""You are an expert credit card rewards strategist. Analyze the following cards:
{cards_list}

Using the card data fetched from official sources below AND your own knowledge, provide a thorough analysis:

1. INDIVIDUAL CARD BREAKDOWN — For each card: annual fee, key earning rates by category, top benefits, lounge access, credits, and ideal user profile.

2. ECOSYSTEM RELATIONSHIPS — Identify which cards share a rewards program or points currency (e.g. Chase Ultimate Rewards, Amex Membership Rewards). For each shared ecosystem:
   - Name the program and list the participating cards.
   - Explain how points can be pooled or transferred between them.
   - Identify the "hub" card that unlocks transfer partners or higher redemption rates.
   - Give concrete point-stacking examples using only the cards listed.

3. OPTIMAL COMBINATIONS — Best 2–3 card combos for:
   - Frequent traveler
   - Everyday spender / cash-back focused
   - Foodie / dining-heavy spender
   Explain why the cards in each combo complement each other.

4. STANDALONE VALUE — For cards with no ecosystem partner in the list, assess standalone value.

5. FINAL RECOMMENDATION — Which card or combo delivers the most value for most people?

Card data:
{context}

Answer:"""

    ask_ollama_stream(prompt)


def run_use(card_names, domain_map, purchase):
    cards_list = ", ".join(card_names)
    print(f"Cards: {cards_list}")
    print(f"Purchase: {purchase}\n")
    print("Fetching card data...\n")

    card_contexts = gather_card_context(card_names, domain_map)
    context = build_card_context_block(card_contexts)

    print(f"\nGathered data for {len(card_contexts)} cards. Asking model...\n")
    print("=" * 60)

    prompt = f"""You are a credit card rewards expert. Use the card data below to answer one question: which card should the user pay with at "{purchase}"?

The user owns these cards:
{cards_list}

Card data (fetched from each card's page — treat stated rates as facts):
{context}

Now respond in this exact format. Replace everything in [brackets]. Do not add any other text or sections.

BEST CHOICE: [Card Name]
Rate: [e.g. 4% cashback on gas]
Why: [Why this card wins for this purchase — 2 sentences max]

ALTERNATIVE 1: [Card Name]
Rate: [rate]
Why: [Why pick this instead — 2 sentences max]

ALTERNATIVE 2: [Card Name]
Rate: [rate]
Why: [Why pick this instead — 2 sentences max]

PRO TIP: [One sentence tip to get even more value from this purchase]"""

    ask_ollama_stream(prompt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Credit card optimizer")
    subparsers = parser.add_subparsers(dest="mode")
    subparsers.add_parser("compare", help="Full card comparison and combo analysis (default)")
    use_parser = subparsers.add_parser("use", help="Pick the best card for a specific purchase")
    use_parser.add_argument("purchase", help='What you are buying, e.g. "groceries" or "flight on Delta"')

    args = parser.parse_args()
    card_names = load_cards()

    print("Resolving card issuer domains...\n")
    domain_map = resolve_issuer_domains(card_names)
    print()

    if args.mode == "use":
        run_use(card_names, domain_map, args.purchase)
    else:
        run_compare(card_names, domain_map)
