"""Local numeric folding and propagation; trapping expressions are retained."""
from dataclasses import replace
from .numeric import is_number, number, evaluate
from .basic_blocks import Block
from .tac import Instr


def _eval(op, x, y):
    try:
        return evaluate(op, x, y)
    except (ArithmeticError, ValueError):
        return None


def fold_block(block):
    environment, output, log = {}, [], []
    for instruction in block.instrs:
        new = replace(instruction)
        if new.kind in ("assign", "binop", "cast", "cond", "return"):
            new.a = environment.get(new.a, new.a)
            new.b = environment.get(new.b, new.b)
        value = None
        if new.kind == "binop" and is_number(new.a) and is_number(new.b):
            value = _eval(new.op, number(new.a), number(new.b))
        elif new.kind == "cast" and is_number(new.a):
            try:
                value = (int if new.op == "int" else float)(number(new.a))
                # Reject a non-finite conversion just as a non-finite literal.
                number(str(value))
            except (ArithmeticError, ValueError):
                value = None
        if value is not None:
            new = Instr("assign", dest=new.dest, a=str(value), line=new.line)
        if new.dest:
            if new.kind == "assign" and is_number(new.a):
                environment[new.dest] = new.a
            else:
                environment.pop(new.dest, None)
        if str(new) != str(instruction): log.append(f"{instruction} => {new}")
        output.append(new)
    return Block(block.name, output), log


def fold_all(blocks):
    results = [fold_block(block) for block in blocks]
    return [b for b, _ in results], {b.name: log for b, log in results}
