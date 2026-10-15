"""
optimizer/algebraic_simplification.py  –  Algebraic simplification pass.

Rules applied per instruction:
  x + 0  →  x           0 + x  →  x
  x - 0  →  x
  x * 1  →  x           1 * x  →  x
  x * 0  →  0           0 * x  →  0
  x / 1  →  x
  x - x  →  0
  x + x  →  2 * x  (kept as   tmp = x * 2  for clarity; not applied here to keep TAC simple)
"""

from dataclasses import replace
from typing import List, Tuple
from .tac import Instr, is_int
from .basic_blocks import Block


_ZERO = "0"
_ONE = "1"


def _simplify(ins: Instr) -> Tuple[Instr, str]:
    """Return (possibly simplified instruction, description of change)."""
    if ins.kind != "binop":
        return ins, ""

    a, op, b = ins.a, ins.op, ins.b

    # x + 0  or  0 + x  →  x
    if op == "+":
        if b == _ZERO:
            return Instr("assign", dest=ins.dest, a=a), f"{ins}  =>  {ins.dest} = {a}"
        if a == _ZERO:
            return Instr("assign", dest=ins.dest, a=b), f"{ins}  =>  {ins.dest} = {b}"

    # x - 0  →  x
    if op == "-":
        if b == _ZERO:
            return Instr("assign", dest=ins.dest, a=a), f"{ins}  =>  {ins.dest} = {a}"
        # x - x  →  0
        if a == b:
            return Instr("assign", dest=ins.dest, a=_ZERO), f"{ins}  =>  {ins.dest} = 0"

    # x * 1  or  1 * x  →  x
    if op == "*":
        if b == _ONE:
            return Instr("assign", dest=ins.dest, a=a), f"{ins}  =>  {ins.dest} = {a}"
        if a == _ONE:
            return Instr("assign", dest=ins.dest, a=b), f"{ins}  =>  {ins.dest} = {b}"
        # x * 0  or  0 * x  →  0
        if b == _ZERO or a == _ZERO:
            return Instr("assign", dest=ins.dest, a=_ZERO), f"{ins}  =>  {ins.dest} = 0"

    # x / 1  →  x
    if op == "/" and b == _ONE:
        return Instr("assign", dest=ins.dest, a=a), f"{ins}  =>  {ins.dest} = {a}"

    return ins, ""


def simplify_block(block: Block) -> Tuple[Block, List[str]]:
    out, log = [], []
    for ins in block.instrs:
        new, msg = _simplify(ins)
        if msg:
            log.append(msg)
        out.append(new)
    return Block(block.name, out), log


def simplify_all(blocks: List[Block]) -> Tuple[List[Block], dict]:
    new_blocks, log = [], {}
    for b in blocks:
        nb, changes = simplify_block(b)
        new_blocks.append(nb)
        log[b.name] = changes
    return new_blocks, log
