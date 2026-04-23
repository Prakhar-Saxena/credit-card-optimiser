import re


def extract_rate_sentences(snippets, purchase):
    """
    Pull out phrases that mention a numeric rate (%, Xx, points/miles per dollar)
    from a list of snippets, sorted so purchase-relevant ones come first.
    Returns a deduplicated list of up to 5 rate mentions.
    """
    purchase_words = set(re.sub(r'[^\w\s]', '', purchase).lower().split())
    rate_pattern = re.compile(
        r'[^.]*\b(\d+(?:\.\d+)?)\s*(?:%|percent|x\b|points? per dollar|miles? per dollar|cash back)[^.]*',
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


def build_card_context_block(card_contexts):
    """Format a list of (name, text) tuples into a labelled context block."""
    return "\n\n".join(f"=== {name} ===\n{text}" for name, text in card_contexts)


def build_rates_table(rate_contexts, purchase):
    """
    Convert raw snippet contexts into a compact rates table suitable for the model prompt.
    Extracts explicit rate mentions; falls back to a 'not mentioned' note.
    """
    lines = []
    for name, text in rate_contexts:
        if text == "[No rate data found]":
            lines.append(f"{name}: no data found")
            continue
        snippets = [s.lstrip("- ") for s in text.splitlines() if s.strip()]
        rate_mentions = extract_rate_sentences(snippets, purchase)
        if rate_mentions:
            lines.append(f"{name}:\n" + "\n".join(f"  • {r}" for r in rate_mentions))
        else:
            lines.append(f"{name}: rate for this category not mentioned in search results")
    return "\n\n".join(lines)
