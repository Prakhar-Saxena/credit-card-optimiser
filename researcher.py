import re

from web import ddg_search, fetch_doc_text
from extractor import extract_rate_sentences, parse_best_rate


# Phrases that indicate a rate is conditional — rotating categories, activation
# required, limited-time promotions, etc.
_CONDITIONAL_PHRASES = [
    'rotating', 'each quarter', 'quarterly', 'activate', 'activation',
    'bonus categor', 'limited time', 'promotional', 'when enrolled',
    'sign up', 'enroll',
]


def _build_offers(all_sources, purchase, card_name, all_card_names):
    """
    Parse structured reward offers from raw text sources.

    Filters out sources that mention another wallet card by name before
    extracting rates, preventing comparison articles from attributing a
    different card's rate to this one.

    Each offer has a `conditional` flag set when the evidence contains
    rotating-category or activation language — these sort below permanent rates.

    Returns (offers, dropped_count) where offers is a list of
    {rate, relevant, conditional, evidence} dicts.
    """
    purchase_words = set(re.sub(r'[^\w\s]', '', purchase).lower().split())
    other_names = [n.lower() for n in all_card_names if n.lower() != card_name.lower()]

    clean_sources = []
    dropped = 0
    for source in all_sources:
        source_lower = source.lower()
        if any(other in source_lower for other in other_names):
            dropped += 1
        else:
            clean_sources.append(source)

    phrases = extract_rate_sentences(clean_sources, purchase)
    offers = []
    seen = set()
    for phrase in phrases:
        numbers = re.findall(r'(?<!\d)(?<!\.)\b(\d+(?:\.\d+)?)\s*%', phrase)
        for n in numbers:
            key = phrase.lower().strip()
            if key not in seen:
                seen.add(key)
                phrase_lower = phrase.lower()
                relevant = any(w in phrase_lower for w in purchase_words)
                conditional = any(p in phrase_lower for p in _CONDITIONAL_PHRASES)
                offers.append({
                    "rate": float(n),
                    "relevant": relevant,
                    "conditional": conditional,
                    "evidence": phrase.strip(),
                })
    # Sort: relevant before general, non-conditional before conditional, rate desc
    offers.sort(key=lambda o: (not o["relevant"], o["conditional"], -o["rate"]))
    return offers, dropped


def research_purchase(card_sources, purchase):
    """
    Phase 2 (use mode) — for each card:
      1. Fetch the official doc URL found in Phase 1 (PDF or terms page).
      2. Also run targeted snippet searches for this purchase category.
      3. Extract structured offers and print a normalized summary.

    Returns a research bundle dict where each card has an `offers` list of
    {rate, relevant, evidence} dicts, making downstream comparison purely
    structural rather than text-parsing.
    """
    print(f'Researching rates for: "{purchase}"\n')
    all_card_names = [c["name"] for c in card_sources]
    cards_data = []

    for card in card_sources:
        name = card["name"]
        url = card.get("url")
        print(f"  [{name}]")

        doc_content = None
        if url:
            print(f"    Fetching doc: {url}")
            doc_content = fetch_doc_text(url)
            if doc_content:
                print(f"    OK — {len(doc_content)} chars")
            else:
                print(f"    Failed or empty")

        # Always also run targeted snippet searches — they often surface
        # the specific rate sentence more directly than a full doc
        q1 = f"{name} {purchase} cashback percent rewards"
        q2 = f"how much does {name} earn on {purchase}"
        _, s1 = ddg_search(q1, max_results=3)
        _, s2 = ddg_search(q2, max_results=2)

        seen = set()
        snippets = []
        for s in s1 + s2:
            if s and s not in seen:
                seen.add(s)
                snippets.append(s)

        all_sources = ([doc_content] if doc_content else []) + snippets
        offers, dropped = _build_offers(all_sources, purchase, name, all_card_names)
        data_source = "official_doc" if doc_content else ("search_snippets" if snippets else "none")

        print(f"    Source: {data_source}")
        if dropped:
            print(f"    Filtered: {dropped} source(s) mentioned other wallet cards")
        if offers:
            print(f"    Offers ({len(offers)}):")
            for o in offers:
                tag = "[relevant]" if o["relevant"] else "[general]"
                print(f"      • {o['rate']}% {tag} — {o['evidence'][:100]}")
        else:
            print(f"    No offers found")

        cards_data.append({
            "name": name,
            "domain": card.get("domain"),
            "url": url,
            "data_source": data_source,
            "offers": offers,
            "doc_content": doc_content,
            "snippets": snippets,
        })
        print()

    return {"purchase": purchase, "cards": cards_data}


def research_compare(card_sources):
    """
    Phase 2 (compare mode) — for each card, fetch its official doc URL and fall
    back to search snippets if the fetch fails.

    Prints fetched content summary and snippets as it gathers them.
    Returns a research bundle dict.
    """
    print("Researching card benefits and features...\n")
    cards_data = []

    for card in card_sources:
        name = card["name"]
        url = card.get("url")
        print(f"  [{name}]")

        doc_content = None
        if url:
            print(f"    Fetching doc: {url}")
            doc_content = fetch_doc_text(url)
            if doc_content:
                print(f"    OK — {len(doc_content)} chars")
                preview = doc_content[:300].replace('\n', ' ')
                print(f"    Preview: {preview}...")
            else:
                print(f"    Failed or empty")

        snippets = []
        if not doc_content:
            query = f"{name} credit card rewards benefits annual fee"
            print(f"    Searching: {query!r}")
            _, snippets = ddg_search(query, max_results=5)
            if snippets:
                print(f"    Snippets ({len(snippets)}):")
                for s in snippets:
                    print(f"      • {s[:140]}")
            else:
                print(f"    No snippets found")

        cards_data.append({
            "name": name,
            "domain": card.get("domain"),
            "url": url,
            "doc_content": doc_content,
            "snippets": snippets,
        })
        print()

    return {"purchase": None, "cards": cards_data}
