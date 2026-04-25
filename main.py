#!/usr/bin/env python3
"""
Credit card optimizer.

Modes:
  compare (default)  Full breakdown, ecosystem relationships, and combo recommendations.
  use                Pick the best card for a specific purchase to maximise rewards.

Usage:
  python main.py
  python main.py compare
  python main.py use "groceries"
  python main.py use "dining at Nobu"
  python main.py use "flight on Delta"
"""

import argparse
from cards import load_cards
from compare import run_compare
from use import run_use


def main():
    parser = argparse.ArgumentParser(description="Credit card optimizer")
    subparsers = parser.add_subparsers(dest="mode")
    subparsers.add_parser("compare", help="Full card comparison and combo analysis (default)")
    use_parser = subparsers.add_parser("use", help="Pick the best card for a specific purchase")
    use_parser.add_argument("purchase", help='What you are buying, e.g. "groceries" or "flight on Delta"')

    args = parser.parse_args()
    card_names = load_cards()

    if args.mode == "use":
        run_use(card_names, args.purchase)
    else:
        run_compare(card_names)


if __name__ == "__main__":
    main()
