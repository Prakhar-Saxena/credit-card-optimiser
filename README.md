# Credit Card Optimiser

A local AI tool that researches your credit cards and tells you which one to use — or gives you a full comparison across your wallet.

Runs entirely on your machine using [Ollama](https://ollama.com) (no API keys, no cloud).

## What it does

**`use` mode** — given a purchase (e.g. "groceries", "flight on Delta"), it:
1. Resolves the issuing bank domain for each of your cards
2. Finds and fetches official documentation (rewards agreements, terms PDFs) from the bank's website
3. Extracts reward rates via regex (no hallucination)
4. Ranks cards by numeric rate and asks the model to explain the recommendation

**`compare` mode** — gives a full breakdown of all your cards: benefits, reward categories, ecosystem relationships (e.g. Chase Ultimate Rewards transfer partners), and combo recommendations.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) running locally with `gemma3:4b` pulled
- Internet access (for DuckDuckGo searches and fetching bank docs)

```bash
ollama pull gemma3:4b
```

## Installation

```bash
git clone git@github.com:Prakhar-Saxena/credit-card-optimiser.git
cd credit-card-optimiser
pip install ddgs pypdf
```

## Configuration

Edit `cards.json` to list your cards:

```json
[
  "Chase Sapphire Reserve",
  "American Express Gold",
  "Citi Double Cash Card"
]
```

At least 2 cards required. Use the full official card name for best results.

## Usage

```bash
# Compare all cards in your wallet
python main.py
python main.py compare

# Pick the best card for a specific purchase
python main.py use "groceries"
python main.py use "flight on Delta"
python main.py use "gas station"
python main.py use "dining at Nobu"
```

## How it works

```
Phase 1 — Resolve   Ask the model for each card's issuing bank domain,
                    then search DDG for official docs (rewards PDFs, terms pages).

Phase 2 — Research  Fetch the doc URL. Also run targeted snippet searches
                    for the specific purchase category. Print everything.

Phase 3 — Synthesise Python extracts and ranks numeric rates from the fetched
                    content. The model only writes explanatory prose —
                    it never decides the winner.
```

## Project structure

| File | Responsibility |
|---|---|
| `main.py` | CLI entry point (argparse) |
| `cards.py` | Load card list from `cards.json` |
| `config.py` | Shared constants (model, URLs, headers) |
| `resolver.py` | Phase 1 — find issuer domain + official doc URL |
| `researcher.py` | Phase 2 — fetch docs and gather search snippets |
| `extractor.py` | Rate extraction, card ranking, context formatting |
| `use.py` | Orchestration for `use` mode |
| `compare.py` | Orchestration for `compare` mode |
| `ollama.py` | Ollama API calls (streaming, temperature=0) |
| `web.py` | DuckDuckGo search, HTML fetch, PDF fetch, URL scoring |

## Built with

- [Claude Code](https://claude.ai/code) — AI pair programmer
- [Ollama](https://ollama.com) — local LLM inference