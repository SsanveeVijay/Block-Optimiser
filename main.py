"""
main.py  –  CLI entry point.

Usage:
    python main.py <file.tac>          # TAC-only pipeline (existing behaviour)
    python main.py --src <file.src>    # Full source pipeline
"""

import sys
from optimizer.pipeline import run, run_source


def print_section(title, text):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)
    print(text)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: python main.py [--src] <file>")

    full_pipeline = False
    if args[0] == "--src":
        full_pipeline = True
        args = args[1:]

    if not args:
        sys.exit("usage: python main.py [--src] <file>")

    with open(args[0]) as f:
        source = f.read()

    if full_pipeline:
        res = run_source(source)
        print_section("AST", res["ast_text"])
        print_section("SEMANTIC ANALYSIS", res["semantic_text"])
        print_section("GENERATED TAC", res["tac_text"])
    else:
        res = run(source)

    print_section("BASIC BLOCKS", res["blocks_text"])
    print_section("CONTROL FLOW GRAPH", res["cfg_text"])
    print_section("AFTER CONSTANT FOLDING", res["folded_text"])
    print_section("AFTER ALGEBRAIC SIMPLIFICATION", res["simplified_text"])
    print_section("AFTER CSE", res["optimised_text"])
    print_section("CHANGE LOG", res["log_text"])


if __name__ == "__main__":
    main()
