import json
import re
from ollama import ask_ollama_raw


def resolve_issuer_domains(card_names):
    """
    Ask the model for the issuing bank's domain for each card.
    Returns a dict mapping card name -> domain string (e.g. "citi.com"), or None if unknown.
    """
    names_block = "\n".join(f"- {n}" for n in card_names)
    prompt = f"""For each credit card below, return the website domain of the BANK or FINANCIAL INSTITUTION that issues the card — not the retail partner. For example:
- "Costco Anywhere Visa Card by Citi" → citi.com  (Citi is the issuing bank, not Costco)
- "Amazon Prime Rewards Visa Signature" → chase.com  (Chase issues it, not Amazon)
- "Chase Sapphire Reserve" → chase.com
- "American Express Platinum" → americanexpress.com

Return a JSON object where each key is the exact card name and the value is the issuing bank's domain. Return ONLY the JSON, no other text.

Cards:
{names_block}

JSON:"""

    raw = ask_ollama_raw(prompt)

    # Accept both {"Card": "domain"} object and ["domain", ...] array
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

    resolved = {}
    for name in card_names:
        domain = domain_map.get(name) or None
        if domain:
            domain = re.sub(r'^https?://', '', str(domain)).split('/')[0].strip()
        resolved[name] = domain
        print(f"  {name}: {domain or 'unknown — will search without site filter'}")

    return resolved
