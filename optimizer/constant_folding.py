from dataclasses import replace
from .tac import is_int
from .basic_blocks import Block
from .tac import Instr


def _eval(op, x, y):
    if op == "+": return x + y
    if op == "-": return x - y
    if op == "*": return x * y
    if op in ("/", "%"):
        if y == 0:
            return None                      
        q = abs(x) // abs(y)
        q = q if (x >= 0) == (y >= 0) else -q
        return q if op == "/" else x - q * y
    cmp = {"<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y,
           "==": x == y, "!=": x != y}
    return int(cmp[op])


def fold_block(block: Block):
    env, out, log = {}, [], []
    for ins in block.instrs:
        new = replace(ins)
        if new.kind in ("assign", "binop", "cond", "return"):
            if new.a is not None:
                new.a = env.get(new.a, new.a)
            if new.b is not None:
                new.b = env.get(new.b, new.b)

        if new.kind == "binop" and is_int(new.a) and is_int(new.b):
            val = _eval(new.op, int(new.a), int(new.b))
            if val is not None:
                new = Instr("assign", dest=new.dest, a=str(val))

        if new.kind in ("assign", "binop"):
            if new.kind == "assign" and is_int(new.a):
                env[new.dest] = new.a
            else:
                env.pop(new.dest, None)

        if str(new) != str(ins):
            log.append(f"{ins}   ==>   {new}")
        out.append(new)
    return Block(block.name, out), log


def fold_all(blocks):
    new_blocks, log = [], {}
    for b in blocks:
        nb, changes = fold_block(b)
        new_blocks.append(nb)
        log[b.name] = changes
    return new_blocks, log
