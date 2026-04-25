from web import ddg_search, fetch_doc_text


def research_purchase(card_sources, purchase):
    """
    Phase 2 (use mode) — for each card:
      1. Fetch the official doc URL found in Phase 1 (PDF or terms page).
      2. Also run targeted snippet searches for this purchase category.
      3. Print everything retrieved so the user can see what's being used.

    Returns a research bundle dict.
    """
    print(f'Researching rates for: "{purchase}"\n')
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
                # Show a preview of what was fetched
                preview = doc_content[:300].replace('\n', ' ')
                print(f"    Preview: {preview}...")
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
