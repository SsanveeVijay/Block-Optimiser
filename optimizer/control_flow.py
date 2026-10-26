"""Simplify constant branches, rebuild blocks, and remove unreachable blocks."""
from .basic_blocks import build_blocks
from .cfg import CFG
from .numeric import is_number, number, evaluate
from .tac import Instr


def simplify_control_flow(blocks):
    instructions, log = [], []
    for block in blocks:
        for ins in block.instrs:
            if ins.kind == "cond" and is_number(ins.a) and is_number(ins.b):
                try:
                    taken = bool(evaluate(ins.op, number(ins.a), number(ins.b)))
                except (ArithmeticError, ValueError):
                    instructions.append(ins)
                    continue
                if taken:
                    replacement = Instr("goto", target=ins.target, line=ins.line)
                    instructions.append(replacement)
                    log.append(f"[{block.name}] {ins} => {replacement} (always true)")
                else:
                    log.append(f"[{block.name}] Removed {ins} (always false)")
            else:
                instructions.append(ins)
    rebuilt = build_blocks(instructions)
    cfg = CFG(rebuilt)
    unreachable = set(cfg.unreachable())
    for block in rebuilt:
        if block.name in unreachable:
            log.append(f"Removed unreachable {block.name}: " + "; ".join(map(str, block.instrs)))
    final = build_blocks([ins for block in rebuilt if block.name not in unreachable for ins in block.instrs])
    return final, CFG(final), log
