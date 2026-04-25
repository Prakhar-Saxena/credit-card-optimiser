from resolver import resolve_card_sources
from researcher import research_purchase
from extractor import rank_cards
from ollama import ask_ollama_stream


def run_use(card_names, purchase):
    # ── Phase 1: Resolve ──────────────────────────────────────────────────────
    print("=" * 60)
    print("PHASE 1 — Resolving card sources")
    print("=" * 60)
    card_sources = resolve_card_sources(card_names)

    # ── Phase 2: Research ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2 — Researching rewards rates")
    print("=" * 60 + "\n")
    research = research_purchase(card_sources, purchase)

    # ── Phase 3: Synthesize ───────────────────────────────────────────────────
    print("=" * 60)
    print("PHASE 3 — Synthesizing")
    print("=" * 60 + "\n")

    ranked = rank_cards(research)

    print("Ranked by rate (Python-parsed):")
    for i, card in enumerate(ranked):
        rate_str = f"{card['rate']}%" if card["rate"] > 0 else "not found"
        print(f"  {i + 1}. {card['name']}: {rate_str}")
        if card["phrase"]:
            print(f"     └ {card['phrase'][:120]}")
    print()

    cards_list = ", ".join(card_names)
    winner = ranked[0]
    alts = ranked[1:3]

    def card_block(card):
        rate_str = f"{card['rate']}%" if card["rate"] > 0 else "not found in search data"
        sources = "\n".join(f"  • {p}" for p in card["rate_phrases"]) if card["rate_phrases"] else "  • (no data)"
        return f"{card['name']}\nRate: {rate_str}\nSource snippets:\n{sources}"

    ranked_block = (
        f"BEST ({winner['name']}):\n{card_block(winner)}\n\n"
        + "\n\n".join(f"ALTERNATIVE {i + 1} ({a['name']}):\n{card_block(a)}" for i, a in enumerate(alts))
    )

    prompt = f"""You are a credit card rewards expert. A user wants to know which card to use at "{purchase}".

The cards have already been ranked by their rewards rate using Python — do not re-rank or second-guess the order.

{ranked_block}

Write the final answer in this exact format. Use the rates and card names exactly as given above.

BEST CHOICE: {winner['name']}
Rate: {f"{winner['rate']}%" if winner['rate'] > 0 else "rate not found"}
Why: [2 sentences explaining why this card wins for this purchase, based on the source snippets]

ALTERNATIVE 1: {alts[0]['name'] if len(alts) > 0 else 'N/A'}
Rate: {f"{alts[0]['rate']}%" if len(alts) > 0 and alts[0]['rate'] > 0 else "rate not found"}
Why: [2 sentences on when to pick this over the winner]

ALTERNATIVE 2: {alts[1]['name'] if len(alts) > 1 else 'N/A'}
Rate: {f"{alts[1]['rate']}%" if len(alts) > 1 and alts[1]['rate'] > 0 else "rate not found"}
Why: [2 sentences on when to pick this over the winner]

PRO TIP: [One sentence tip to squeeze more value from this purchase]"""

    ask_ollama_stream(prompt)
