from resolver import resolve_card_sources
from researcher import research_purchase
from extractor import rank_cards
from ollama import ask_ollama_stream
from categorizer import identify_purchase_category
from timer import Timer


def run_use(card_names, purchase):
    t = Timer()

    # ── Phase 1: Resolve ──────────────────────────────────────────────────────
    print("=" * 60)
    print(f"PHASE 1 — Resolving card sources  {t.ts()}")
    print("=" * 60)
    card_sources = resolve_card_sources(card_names)

    # ── Phase 2: Research ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"PHASE 2 — Researching rewards rates  {t.ts()}")
    print("=" * 60 + "\n")

    identified = identify_purchase_category(purchase)
    category = identified["category"]
    merchant = identified.get("merchant")
    if category.lower() != purchase.lower():
        merchant_str = f" ({merchant})" if merchant else ""
        print(f'  Identified: "{purchase}"{merchant_str} → {category}\n')

    research = research_purchase(card_sources, purchase, t, category)

    # ── Phase 3: Synthesize ───────────────────────────────────────────────────
    print("=" * 60)
    print(f"PHASE 3 — Synthesizing  {t.ts()}")
    print("=" * 60 + "\n")

    ranked = rank_cards(research)

    print("Ranked by rate (Python-parsed):")
    for i, card in enumerate(ranked):
        if card["is_fallback"]:
            rate_str = f"~{card['rate']}% (est. base)"
        elif card["is_conditional"]:
            rate_str = f"{card['rate']}% (conditional)"
        else:
            rate_str = f"{card['rate']}%"
        print(f"  {i + 1}. {card['name']}: {rate_str}")
        if card["phrase"]:
            print(f"     └ {card['phrase'][:120]}")
        if card.get("url"):
            print(f"     └ Source: {card['url']}")
    print()

    cards_list = ", ".join(card_names)
    winner = ranked[0]
    alts = ranked[1:3]

    def card_block(card):
        rate_str = f"~{card['rate']}% (estimated base rate — no category-specific data found)" if card["is_fallback"] else f"{card['rate']}%"
        sources = "\n".join(f"  • {p}" for p in card["rate_phrases"]) if card["rate_phrases"] else "  • (no data)"
        source_url = f"\nSource document: {card['url']}" if card.get("url") else ""
        return f"{card['name']}\nRate: {rate_str}\nSource snippets:\n{sources}{source_url}"

    ranked_block = (
        f"BEST ({winner['name']}):\n{card_block(winner)}\n\n"
        + "\n\n".join(f"ALTERNATIVE {i + 1} ({a['name']}):\n{card_block(a)}" for i, a in enumerate(alts))
    )

    def rate_label(card):
        if card["is_fallback"]:
            return f"~{card['rate']}% (estimated base rate)"
        if card["is_conditional"]:
            return f"{card['rate']}% (conditional — requires activation or rotating category)"
        return f"{card['rate']}%"

    prompt = f"""You are a credit card rewards expert. A user wants to know which card to use at "{purchase}".

The cards have already been ranked by their rewards rate using Python — do not re-rank or second-guess the order.
Rates marked as "estimated base rate" mean no category-specific data was found; treat them as approximate.
Rates marked as "conditional" require activation or apply only during rotating quarterly categories — mention this caveat.

{ranked_block}

Write the final answer in this exact format. Use the rates and card names exactly as given above.

BEST CHOICE: {winner['name']}
Rate: {rate_label(winner)}
Source: {winner['url'] if winner.get('url') else "search snippets"}
Why: [2 sentences explaining why this card wins for this purchase, based on the source snippets]

ALTERNATIVE 1: {alts[0]['name'] if len(alts) > 0 else 'N/A'}
Rate: {rate_label(alts[0]) if len(alts) > 0 else "N/A"}
Why: [2 sentences on when to pick this over the winner]

ALTERNATIVE 2: {alts[1]['name'] if len(alts) > 1 else 'N/A'}
Rate: {rate_label(alts[1]) if len(alts) > 1 else "N/A"}
Why: [2 sentences on when to pick this over the winner]

PRO TIP: [One sentence tip to squeeze more value from this purchase]"""

    ask_ollama_stream(prompt)
