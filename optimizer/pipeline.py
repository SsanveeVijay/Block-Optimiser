"""
optimizer/pipeline.py  –  Orchestrates the full compiler pipeline.

Two entry points:
  run(source)        – TAC input (legacy / direct TAC mode)
  run_source(source) – Full pipeline: source language →
                         Lex → Parse → Semantic → Codegen → Optimise
"""

from .tac import parse
from .basic_blocks import build_blocks
from .cfg import CFG
from .constant_folding import fold_all
from .algebraic_simplification import simplify_all
from .cse import cse_all


# --------------------------------------------------------------------------- #
#  Formatting helpers                                                          #
# --------------------------------------------------------------------------- #

def fmt_blocks(blocks):
    lines = []
    for b in blocks:
        lines.append(f"{b.name}:")
        lines.extend(f"    {i}" for i in b.instrs)
        lines.append("")
    return "\n".join(lines)


def fmt_cfg(cfg):
    lines = []
    for b in cfg.blocks:
        s = ", ".join(cfg.succ[b.name]) or "(exit)"
        p = ", ".join(cfg.pred[b.name]) or "(entry)"
        lines.append(f"{b.name}:  preds = {p}   succs = {s}")
    lines.append("")
    lines.append("Edges: " + ", ".join(f"{a}->{b}" for a, b in cfg.edges()))
    un = cfg.unreachable()
    lines.append("Unreachable blocks: " + (", ".join(un) if un else "none"))
    return "\n".join(lines)


def _fmt_log(log):
    return (
        "\n".join(f"[{n}] {c}" for n, ch in log.items() for c in ch)
        or "  (none)"
    )


def _optimise(blocks):
    """Run the three optimisation passes and return enriched result dict."""
    cfg = CFG(blocks)

    # Pass 1: Constant folding
    folded, fold_log = fold_all(blocks)

    # Pass 2: Algebraic simplification
    simplified, alg_log = simplify_all(folded)

    # Pass 3: CSE
    cse_blocks, cse_log = cse_all(simplified)

    return {
        "blocks": blocks,
        "cfg": cfg,
        "folded": folded,
        "simplified": simplified,
        "optimised": cse_blocks,
        "fold_log": fold_log,
        "alg_log": alg_log,
        "cse_log": cse_log,
        # ---- text versions ----
        "blocks_text": fmt_blocks(blocks),
        "cfg_text": fmt_cfg(cfg),
        "folded_text": fmt_blocks(folded),
        "simplified_text": fmt_blocks(simplified),
        "optimised_text": fmt_blocks(cse_blocks),
        "log_text": (
            "=== Constant Folding ===\n" + _fmt_log(fold_log) + "\n\n"
            "=== Algebraic Simplification ===\n" + _fmt_log(alg_log) + "\n\n"
            "=== Common Subexpression Elimination ===\n" + _fmt_log(cse_log)
        ),
    }


# --------------------------------------------------------------------------- #
#  Public entry points                                                         #
# --------------------------------------------------------------------------- #

def run(source: str) -> dict:
    """
    Legacy TAC-only pipeline.
    Input: raw three-address code text.
    """
    prog = parse(source)
    blocks = build_blocks(prog)
    return _optimise(blocks)


def run_source(source: str) -> dict:
    """
    Full compiler pipeline.
    Input: simple C-like source code.
    Returns the same keys as run() PLUS:
      ast, ast_text, semantic_issues, tac_lines, tac_text
    """
    from .parser_ast import parse_source, ast_to_str
    from .semantic import analyse
    from .codegen import generate, tac_lines_to_str

    # 1. Syntax analysis (lex + parse)
    ast = parse_source(source)
    ast_text = ast_to_str(ast)

    # 2. Semantic analysis
    _analyser, semantic_text = analyse(ast)

    # 3. Intermediate code generation (TAC)
    tac_lines = generate(ast)
    tac_text = tac_lines_to_str(tac_lines)

    # 4. Parse generated TAC and run optimisation passes
    prog = parse(tac_text)
    blocks = build_blocks(prog)
    result = _optimise(blocks)

    result.update({
        "ast": ast,
        "ast_text": ast_text,
        "semantic_text": semantic_text,
        "tac_lines": tac_lines,
        "tac_text": tac_text,
        "mode": "source",
    })
    return result
