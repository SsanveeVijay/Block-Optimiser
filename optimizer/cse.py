"""Local CSE invalidates changed operands and overwritten result holders."""
from .basic_blocks import Block
from .tac import Instr


def cse_block(block):
    available, out, log = {}, [], []
    for ins in block.instrs:
        key = (ins.a, ins.op, ins.b) if ins.kind == "binop" else None
        previous = available.get(key)
        if ins.dest:
            available = {k: holder for k, holder in available.items()
                         if ins.dest not in (k[0], k[2], holder)}
        new = ins
        if previous is not None:
            new = Instr("assign", dest=ins.dest, a=previous, line=ins.line)
            log.append(f"{ins} => {new} (CSE: reuse {previous})")
        # Self-updating operands no longer describe the original expression.
        if key and ins.dest not in (ins.a, ins.b):
            available[key] = ins.dest
        out.append(new)
    return Block(block.name, out), log


def cse_all(blocks):
    results = [cse_block(block) for block in blocks]
    return [b for b, _ in results], {b.name: log for b, log in results}
