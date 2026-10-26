"""Command-line interface for the basic-block compiler and optimizer."""
import argparse
from pathlib import Path
import sys
from optimizer.pipeline import run, run_source
from optimizer.diagnostics import CompilationError

SECTIONS = [
    ("TOKENS", "tokens_text"), ("AST", "ast_text"),
    ("SEMANTIC ANALYSIS", "semantic_text"), ("SYMBOLS", "symbols_text"),
    ("GENERATED TAC", "tac_text"), ("BASIC BLOCKS", "blocks_text"),
    ("ORIGINAL CONTROL-FLOW GRAPH", "cfg_text"),
    ("AFTER CONSTANT FOLDING", "folded_text"),
    ("AFTER ALGEBRAIC SIMPLIFICATION", "simplified_text"),
    ("AFTER CSE", "cse_text"), ("FINAL OPTIMIZED TAC", "optimised_text"),
    ("FINAL CONTROL-FLOW GRAPH", "final_cfg_text"),
    ("CHANGE LOG", "log_text"), ("IMPACT REPORT", "impact_text"),
    ("DIAGNOSTICS", "diagnostics_text"),
]


def print_results(result):
    for title, key in SECTIONS:
        if key in result:
            print("\n" + "=" * 60 + "\n" + title + "\n" + "=" * 60)
            print(result[key])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile a small C-like language or optimize TAC.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--src", action="store_true", help="Force source mode")
    mode.add_argument("--tac", action="store_true", help="Force direct TAC mode")
    parser.add_argument("file", type=Path, help="UTF-8 .src or .tac input file")
    args = parser.parse_args(argv)
    try:
        source = args.file.read_text(encoding="utf-8-sig")
        is_source = args.src or (not args.tac and args.file.suffix.lower() == ".src")
        result = (run_source if is_source else run)(source)
    except (OSError, UnicodeError) as error:
        print(f"[File input] {error}", file=sys.stderr)
        return 1
    except CompilationError as error:
        print_results(error.partial_result)
        print(error, file=sys.stderr)
        return 1
    except RecursionError:
        print("[Input] Nesting is too deep; simplify the program.", file=sys.stderr)
        return 1
    print_results(result)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
        sys.stderr.reconfigure(errors="backslashreplace")
    sys.exit(main())
