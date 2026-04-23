from web import ddg_search, fetch_page_text


def gather_card_context(card_names, domain_map):
    """
    For each card, search DDG scoped to the issuer's domain, fetch the first
    working page, and fall back to snippets if no page is fetchable.
    Returns a list of (card_name, text) tuples.
    """
    results = []
    for name in card_names:
        domain = domain_map.get(name)
        base_query = f"{name} credit card rewards benefits"
        site_query = f"site:{domain} {base_query}" if domain else base_query

        print(f"  [{name}]")
        print(f"    Searching: {site_query!r}")
        urls, snippets = ddg_search(site_query)

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


def gather_category_rates(card_names, purchase):
    """
    For each card, run two targeted searches to surface the specific rewards
    rate for the given purchase category.
    Returns a list of (card_name, snippets_text) tuples.
    """
    results = []
    for name in card_names:
        q1 = f"{name} {purchase} cashback percent rewards"
        q2 = f"how much does {name} earn on {purchase}"

        print(f"  [{name}]")
        _, s1 = ddg_search(q1, max_results=3)
        _, s2 = ddg_search(q2, max_results=2)

        seen = set()
        snippets = []
        for s in s1 + s2:
            if s and s not in seen:
                seen.add(s)
                snippets.append(s)

        if snippets:
            print(f"    {len(snippets)} snippet(s) found")
            results.append((name, "\n".join(f"- {s}" for s in snippets)))
        else:
            print(f"    No snippets found")
            results.append((name, "[No rate data found]"))

    return results
