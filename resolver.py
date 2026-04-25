import json
import re
from ollama import ask_ollama_raw
from web import ddg_search, score_doc_url


def resolve_card_sources(card_names):
    """
    Phase 1 — for each card, ask the model for the issuing bank's domain,
    then search DDG specifically for official documentation (rewards agreements,
    terms pages, offer details, PDFs).

    Prints domain + doc URL for each card.
    Returns: [{"name", "domain", "url"}, ...]
    """
    domain_map = _ask_model_for_domains(card_names)

    results = []
    for name in card_names:
        domain = domain_map.get(name)
        doc_url = _find_doc_url(name, domain) if domain else None

        print(f"  {name}")
        print(f"    Issuer domain : {domain or 'unknown'}")
        print(f"    Docs URL      : {doc_url or 'not found — will rely on search snippets'}")

        results.append({"name": name, "domain": domain, "url": doc_url})

    return results


def _find_doc_url(card_name, domain):
    """
    Search for official documentation for a card on its issuer's domain.
    Tries multiple doc-targeted queries and scores URLs by documentation keywords.
    Falls back to an open search if the site-scoped search finds nothing.
    """
    queries = [
        f'site:{domain} "{card_name}" rewards program agreement',
        f'site:{domain} "{card_name}" offer details terms',
        f'site:{domain} {card_name} cardmember agreement',
        f'site:{domain}/us "{card_name}" rewards',
    ]

    best_url, best_score = None, -1

    for query in queries:
        urls, _ = ddg_search(query, max_results=5)
        for url in urls:
            score = score_doc_url(url)
            if score > best_score:
                best_score = score
                best_url = url
        if best_score > 0:
            break

    # If nothing doc-like found on the issuer domain, try an open search
    if best_score <= 0:
        urls, _ = ddg_search(f'"{card_name}" rewards program agreement terms official', max_results=5)
        for url in urls:
            if domain in url:
                score = score_doc_url(url)
                if score > best_score:
                    best_score = score
                    best_url = url

    return best_url


def _ask_model_for_domains(card_names):
    """Ask the model for each card's issuing bank domain. Returns {name: domain}."""
    names_block = "\n".join(f"- {n}" for n in card_names)
    prompt = f"""For each credit card below, return the website domain of the BANK or FINANCIAL INSTITUTION that issues the card — not the retail partner. For example:
- "Costco Anywhere Visa Card by Citi" → citi.com  (Citi issues it, not Costco)
- "Amazon Prime Rewards Visa" → chase.com  (Chase issues it, not Amazon)
- "Chase Sapphire Reserve" → chase.com
- "American Express Platinum" → americanexpress.com

Return a JSON object where each key is the exact card name and the value is the issuing bank domain. Return ONLY the JSON, no other text.

Cards:
{names_block}

JSON:"""

    raw = ask_ollama_raw(prompt)

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

    # Domains that geo-redirect to non-US pages — map to the correct US domain
    _DOMAIN_FIXES = {
        "citibank.com": "citi.com",
    }

    cleaned = {}
    for name in card_names:
        domain = domain_map.get(name) or None
        if domain:
            domain = re.sub(r'^https?://', '', str(domain)).split('/')[0].strip()
            domain = _DOMAIN_FIXES.get(domain, domain)
        cleaned[name] = domain

    return cleaned
