import re


def extract_rate_sentences(snippets, purchase):
    """
    Pull out phrases that mention a numeric rate (%, Xx, points/miles per dollar)
    from a list of snippets, sorted so purchase-relevant ones come first.
    Returns a deduplicated list of up to 5 rate mentions.
    """
    purchase_words = set(re.sub(r'[^\w\s]', '', purchase).lower().split())
    rate_pattern = re.compile(
        r'[^.]*(?<!\d)(?<!\.)\b(\d+(?:\.\d+)?)\s*(?:%|percent|x\b|points? per dollar|miles? per dollar|cash back)[^.]*',
        re.IGNORECASE
    )

    seen = set()
    hits = []
    for snippet in snippets:
        for match in rate_pattern.finditer(snippet):
            phrase = match.group().strip()
            key = re.sub(r'\s+', ' ', phrase.lower())
            if key not in seen:
                seen.add(key)
                relevant = any(w in key for w in purchase_words)
                hits.append((relevant, phrase))

    hits.sort(key=lambda x: not x[0])
    return [phrase for _, phrase in hits[:5]]


def parse_best_rate(rate_phrases, purchase):
    """
    From a list of rate phrases, find the highest percentage rate that is
    explicitly relevant to the purchase category.
    Falls back to the highest rate in any phrase if none are category-specific.
    Returns (rate_value: float, source_phrase: str).
    """
    purchase_words = set(re.sub(r'[^\w\s]', '', purchase).lower().split())

    relevant_best = (0.0, "")
    fallback_best = (0.0, "")

    for phrase in rate_phrases:
        numbers = re.findall(r'(?<!\d)(?<!\.)\b(\d+(?:\.\d+)?)\s*%', phrase)
        for n in numbers:
            val = float(n)
            is_relevant = any(w in phrase.lower() for w in purchase_words)
            if is_relevant and val > relevant_best[0]:
                relevant_best = (val, phrase)
            if val > fallback_best[0]:
                fallback_best = (val, phrase)

    return relevant_best if relevant_best[0] > 0 else fallback_best


_BASE_RATE = 1.0  # conservative fallback when no category-specific rate is found


def rank_cards(research_bundle):
    """
    Rank cards best-to-worst using pre-structured offers from the research bundle.
    Only relevant offers (matching the purchase category) drive the rate; general
    offers are never used for ranking. Cards with no relevant offer fall back to
    _BASE_RATE and are flagged with is_fallback=True.

    Each entry:
      {"name", "rate", "is_fallback", "phrase", "rate_phrases", "url", "domain"}
    """
    ranked = []

    for card in research_bundle["cards"]:
        offers = card.get("offers") or []
        relevant = [o for o in offers if o["relevant"]]

        if relevant:
            best = relevant[0]  # sorted: non-conditional first, then by rate desc
            rate_val = best["rate"]
            best_phrase = best["evidence"]
            is_fallback = False
            # If any relevant offer at this rate has conditional language, the
            # rate is conditional — a single clean-looking phrase doesn't mean
            # the program itself is unconditional
            is_conditional = any(
                o["conditional"] and o["rate"] >= rate_val for o in relevant
            )
        else:
            rate_val = _BASE_RATE
            best_phrase = ""
            is_fallback = True
            is_conditional = False

        ranked.append({
            "name": card["name"],
            "rate": rate_val,
            "is_fallback": is_fallback,
            "is_conditional": is_conditional,
            "phrase": best_phrase,
            "rate_phrases": [o["evidence"] for o in offers],
            "url": card.get("url"),
            "domain": card.get("domain"),
        })

    # Verified non-conditional > verified conditional > fallback
    ranked.sort(key=lambda c: (c["is_fallback"], c["is_conditional"], -c["rate"]))
    return ranked


def build_card_context_block(research_bundle):
    """Format researched card data into a labelled context block for the model."""
    sections = []
    for card in research_bundle["cards"]:
        content = (
            card.get("doc_content")
            or card.get("content")
            or "\n".join(f"- {s}" for s in card.get("snippets", []))
        )
        source = card.get("url") or "search snippets"
        sections.append(f"=== {card['name']} (source: {source}) ===\n{content or '[No data retrieved]'}")
    return "\n\n".join(sections)
