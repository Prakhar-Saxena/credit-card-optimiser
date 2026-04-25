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


def rank_cards(research_bundle):
    """
    Parse numeric rates from each card's snippets in the research bundle and
    return a list sorted best-to-worst for the purchase.

    Each entry:
      {"name", "rate", "phrase", "rate_phrases", "url", "domain"}
    """
    purchase = research_bundle["purchase"]
    ranked = []

    for card in research_bundle["cards"]:
        snippets = card.get("snippets") or []
        # Official doc content is the most authoritative — prepend it
        if card.get("doc_content"):
            snippets = [card["doc_content"]] + snippets
        elif card.get("content"):
            snippets = [card["content"]] + snippets

        phrases = extract_rate_sentences(snippets, purchase)
        rate_val, best_phrase = parse_best_rate(phrases, purchase)

        ranked.append({
            "name": card["name"],
            "rate": rate_val,
            "phrase": best_phrase,
            "rate_phrases": phrases,
            "url": card.get("url"),
            "domain": card.get("domain"),
        })

    ranked.sort(key=lambda c: c["rate"], reverse=True)
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
