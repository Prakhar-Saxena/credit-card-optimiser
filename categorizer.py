import json
import re

from ollama import ask_ollama_raw


def identify_purchase_category(raw_purchase):
    """
    Map a raw purchase description to a credit card rewards category.
    "Shell" → "gas stations", "Target" → "department stores", etc.
    Returns {"category": str, "merchant": str|None}.
    Falls back to the original string if the model can't classify.
    """
    prompt = f"""A user is about to pay at: "{raw_purchase}"

Your job: identify the credit card rewards category this purchase falls under.
Credit card issuers use categories like: gas stations, grocery stores, restaurants,
dining, travel, airfare, hotels, department stores, clothing stores, drugstores,
home improvement, online shopping, streaming services, utilities, entertainment, transit.

Return a JSON object with exactly these two keys:
- "merchant": the business or brand name if recognisable (e.g. "Shell", "Target"), otherwise null
- "category": the rewards category string that card issuers would use (2-4 words, lowercase)

Examples:
"Shell" → {{"merchant": "Shell", "category": "gas stations"}}
"Target" → {{"merchant": "Target", "category": "department stores"}}
"Old Navy" → {{"merchant": "Old Navy", "category": "clothing stores"}}
"dining at Nobu" → {{"merchant": "Nobu", "category": "restaurants"}}
"flight on Delta" → {{"merchant": "Delta", "category": "airfare"}}
"groceries" → {{"merchant": null, "category": "grocery stores"}}
"Walgreens" → {{"merchant": "Walgreens", "category": "drugstores"}}
"Netflix" → {{"merchant": "Netflix", "category": "streaming services"}}

Return ONLY the JSON, no other text.

JSON:"""

    raw = ask_ollama_raw(prompt)
    obj_match = re.search(r'\{.*?\}', raw, re.DOTALL)
    if obj_match:
        try:
            result = json.loads(obj_match.group())
            category = (result.get("category") or raw_purchase).strip().lower()
            merchant = result.get("merchant") or None
            return {"category": category, "merchant": merchant}
        except (json.JSONDecodeError, AttributeError):
            pass
    return {"category": raw_purchase, "merchant": None}
