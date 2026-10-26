"""Shared source/TAC pipeline. Errors expose only completed stages."""
from .tac import parse
from .basic_blocks import build_blocks
from .cfg import CFG
from .constant_folding import fold_all
from .algebraic_simplification import simplify_all
from .cse import cse_all
from .control_flow import simplify_control_flow
from .impact_analyzer import analyze
from .diagnostics import CompilationError
from .numeric import is_number, number


def fmt_blocks(blocks):
    return "\n\n".join(b.name + ":\n" + "\n".join(f"    {i}" for i in b.instrs) for b in blocks) or "(empty program)"


def fmt_cfg(cfg):
    lines = [f"{b.name}: preds = {', '.join(cfg.pred[b.name]) or '(entry)'}; "
             f"succs = {', '.join(cfg.succ[b.name]) or '(exit)'}" for b in cfg.blocks]
    lines.append("Edges: " + (", ".join(f"{a}->{b}" for a, b in cfg.edges()) or "none"))
    lines.append("Unreachable blocks: " + (", ".join(cfg.unreachable()) or "none"))
    return "\n".join(lines)


def _fmt_log(log):
    return "\n".join(f"[{name}] {change}" for name, changes in log.items() for change in changes) or "(none)"


def _optimise(blocks, integer_only=True):
    result = {"blocks": blocks, "blocks_text": fmt_blocks(blocks)}
    try:
        cfg = CFG(blocks)
        result.update(cfg=cfg, cfg_text=fmt_cfg(cfg))
        folded, fold_log = fold_all(blocks)
        simplified, alg_log = simplify_all(folded, integer_only=integer_only)
        cse_blocks, cse_log = cse_all(simplified)
        final, final_cfg, flow_log = simplify_control_flow(cse_blocks)
        impact = analyze(blocks, [("Constant Folding", folded),
                                 ("Algebraic Simplification", simplified),
                                 ("Common Subexpression Elimination", cse_blocks),
                                 ("Control-flow Cleanup", final)])
        warnings = []
        if not integer_only:
            warnings.append("NOTE: Integer algebraic identities skipped because this program uses float values.")
        for block in folded:
            for ins in block.instrs:
                if ins.op in ("/", "%") and is_number(ins.b) and number(ins.b) == 0:
                    warnings.append(f"WARNING: TAC line {ins.line}: zero divisor retained; expression is not evaluated by the optimizer.")
        result.update(folded=folded, simplified=simplified, cse_blocks=cse_blocks, optimised=final,
            final_cfg=final_cfg, fold_log=fold_log, alg_log=alg_log, cse_log=cse_log, flow_log=flow_log,
            folded_text=fmt_blocks(folded), simplified_text=fmt_blocks(simplified),
            cse_text=fmt_blocks(cse_blocks), optimised_text=fmt_blocks(final), final_cfg_text=fmt_cfg(final_cfg),
            impact=impact, impact_text=impact.summary_text(), diagnostics_text="\n".join(warnings) or "No errors or warnings.",
            log_text="=== Constant Folding ===\n" + _fmt_log(fold_log)
                + "\n\n=== Algebraic Simplification ===\n" + _fmt_log(alg_log)
                + "\n\n=== Common Subexpression Elimination ===\n" + _fmt_log(cse_log)
                + "\n\n=== Control-flow Cleanup ===\n" + ("\n".join(flow_log) or "(none)"))
        return result
    except CompilationError as error:
        error.partial_result = {**result, **error.partial_result}
        raise


def run(source):
    program = parse(source)
    integer_only = not any(ins.kind == "cast" and ins.op == "float" or
                           any(is_number(v) and isinstance(number(v), float) for v in (ins.a, ins.b))
                           for ins in program)
    result = _optimise(build_blocks(program), integer_only)
    result["mode"] = "tac"
    return result


def run_source(source):
    from .lexer import tokenize, format_tokens
    from .parser_ast import Parser, ast_to_str
    from .semantic import analyse
    from .codegen import generate
    result = {"mode": "source"}
    try:
        tokens = tokenize(source)
        result.update(tokens=tokens, tokens_text=format_tokens(tokens))
        ast = Parser(tokens).parse()
        result.update(ast=ast, ast_text=ast_to_str(ast))
        analyser, semantic_text = analyse(ast)
        symbol_text = "\n".join(f"{s.name} ({s.typ}, line {s.declared_line}) -> {s.tac_name}" for s in analyser.symbols)
        result.update(semantic_text=semantic_text, symbols_text=symbol_text or "(no symbols)")
        if any(issue.level == "error" for issue in analyser.issues):
            raise CompilationError("Semantic analysis", semantic_text)
        tac_lines = generate(ast)
        tac_text = "\n".join(tac_lines)
        result.update(tac_lines=tac_lines, tac_text=tac_text)
        integer_only = not any(t.kind == "FLOAT" or
                               t.kind == "NUMBER" and isinstance(number(t.value), float)
                               for t in tokens)
        result.update(_optimise(build_blocks(parse(tac_text)), integer_only))
        if analyser.issues:
            notes = result["diagnostics_text"]
            result["diagnostics_text"] = semantic_text + ("\n" + notes if notes != "No errors or warnings." else "")
        return result
    except CompilationError as error:
        error.partial_result = {**result, **error.partial_result}
        error.partial_result["diagnostics_text"] = str(error)
        raise
