from resolver import resolve_card_sources
from researcher import research_compare
from extractor import build_card_context_block
from ollama import ask_ollama_stream
from web import ddg_search
from timer import Timer


def run_compare(card_names):
    t = Timer()

    # ── Phase 1: Resolve ──────────────────────────────────────────────────────
    print("=" * 60)
    print(f"PHASE 1 — Resolving card sources  {t.ts()}")
    print("=" * 60)
    card_sources = resolve_card_sources(card_names)

    # ── Phase 2: Research ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"PHASE 2 — Researching card benefits  {t.ts()}")
    print("=" * 60 + "\n")
    research = research_compare(card_sources, t)

    print("Searching: ecosystem and combination strategies...")
    _, synergy_snippets = ddg_search(
        " ".join(card_names) + " credit card points pooling transfer strategy"
    )
    if synergy_snippets:
        print(f"  {len(synergy_snippets)} synergy snippet(s) found:")
        for s in synergy_snippets:
            print(f"  • {s[:140]}")

    # ── Phase 3: Synthesize ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"PHASE 3 — Synthesizing  {t.ts()}")
    print("=" * 60 + "\n")

    context = build_card_context_block(research)
    if synergy_snippets:
        context += "\n\n=== Ecosystem & Combination Strategies ===\n" + "\n".join(f"- {s}" for s in synergy_snippets)

    cards_list = ", ".join(card_names)

    prompt = f"""You are an expert credit card rewards strategist. Analyze the following cards:
{cards_list}

Using the card data below AND your own knowledge, provide a thorough analysis:

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
