from .tac import parse
from .basic_blocks import build_blocks
from .cfg import CFG
from .constant_folding import fold_all


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


def run(source: str) -> dict:
    prog = parse(source)
    blocks = build_blocks(prog)
    cfg = CFG(blocks)
    folded, log = fold_all(blocks)
    return {
        "blocks": blocks, "cfg": cfg, "folded": folded, "log": log,
        "blocks_text": fmt_blocks(blocks),
        "cfg_text": fmt_cfg(cfg),
        "folded_text": fmt_blocks(folded),
        "log_text": "\n".join(
            f"[{n}] {c}" for n, ch in log.items() for c in ch
        ) or "No constants folded.",
    }
