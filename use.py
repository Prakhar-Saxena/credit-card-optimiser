from gatherer import gather_category_rates
from extractor import build_rates_table
from ollama import ask_ollama_stream


def run_use(card_names, purchase):
    cards_list = ", ".join(card_names)
    print(f"Cards: {cards_list}")
    print(f"Purchase: {purchase}\n")

    print("Searching category-specific rates for each card...\n")
    rate_contexts = gather_category_rates(card_names, purchase)

    rates_table = build_rates_table(rate_contexts, purchase)
    print(f"\nExtracted rates:\n{rates_table}\n")
    print("=" * 60)

    prompt = f"""You are a credit card rewards expert. A user wants to know which card to use at "{purchase}".

The user owns these cards:
{cards_list}

Below are the VERIFIED rewards rates for each card at "{purchase}", extracted from live search results. These are facts — do not contradict them, do not substitute your own knowledge.

{rates_table}

Using only the rates above, respond in this exact format. Only recommend cards from the user's list.

BEST CHOICE: [Card Name]
Rate: [rate from the table above]
Why: [Why this card wins — 2 sentences max]

ALTERNATIVE 1: [Card Name]
Rate: [rate from the table above]
Why: [Why this is a solid second choice — 2 sentences max]

ALTERNATIVE 2: [Card Name]
Rate: [rate from the table above]
Why: [Why this is worth considering — 2 sentences max]

PRO TIP: [One sentence tip to squeeze more value from this purchase]"""

    ask_ollama_stream(prompt)
