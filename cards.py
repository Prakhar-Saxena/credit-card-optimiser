import json
import sys
from config import CARDS_FILE


def load_cards(path=CARDS_FILE):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list) or len(data) < 2:
        print(f"Error: {path} must be a JSON array with at least 2 card names.", file=sys.stderr)
        sys.exit(1)
    return [str(c) for c in data]
