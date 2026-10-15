"""
optimizer/cse.py  –  Local Common Subexpression Elimination (CSE).

Within each basic block, if the same binop expression (a op b) has already
been computed and neither a nor b has been redefined since, reuse the
previously computed temporary instead of recomputing.
"""

from typing import List, Dict, Tuple, Optional
from .tac import Instr
from .basic_blocks import Block


def _expr_key(ins: Instr) -> Optional[Tuple[str, str, str]]:
    """Return a hashable key for a binop, or None if not applicable."""
    if ins.kind == "binop":
        return (ins.a, ins.op, ins.b)
    return None


def cse_block(block: Block) -> Tuple[Block, List[str]]:
    """Eliminate common subexpressions within a single basic block."""
    # Maps (a, op, b) -> variable name that holds that value
    available: Dict[Tuple[str, str, str], str] = {}
    # Track which expressions become unavailable when a variable is redefined
    # (mapping var_name -> set of expr keys that use it)
    uses: Dict[str, set] = {}

    out, log = [], []

    for ins in block.instrs:
        key = _expr_key(ins)
        if key and key in available:
            # Replace with assignment from already-computed value
            prev = available[key]
            new = Instr("assign", dest=ins.dest, a=prev)
            log.append(f"{ins}  =>  {new}  (CSE: reuse {prev})")
            # Register the new dest as an alias
            available[key] = ins.dest   # keep mapping, update dest for future refs
            _invalidate(available, uses, ins.dest)
            available[key] = prev       # restore for subsequent uses
            # Track that dest now holds this expression's value too
            out.append(new)
        else:
            if key:
                _invalidate(available, uses, ins.dest)
                available[key] = ins.dest
                # Record that this expression uses ins.a and ins.b
                for var in (ins.a, ins.b):
                    if var not in uses:
                        uses[var] = set()
                    uses[var].add(key)
            elif ins.kind in ("assign", "binop") and ins.dest:
                # Destination is being defined; invalidate any expr that used it
                _invalidate(available, uses, ins.dest)
            out.append(ins)

    return Block(block.name, out), log


def _invalidate(available, uses, var):
    """Remove all expressions from 'available' that depend on 'var'."""
    for key in list(uses.get(var, [])):
        available.pop(key, None)
    uses.pop(var, None)


def cse_all(blocks: List[Block]) -> Tuple[List[Block], dict]:
    new_blocks, log = [], {}
    for b in blocks:
        nb, changes = cse_block(b)
        new_blocks.append(nb)
        log[b.name] = changes
    return new_blocks, log
