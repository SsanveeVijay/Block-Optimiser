"""Independent, bounded TAC executor used only to verify behavior in tests."""
import math
import re


def execute(instructions, inputs=None, limit=10000):
    env = dict(inputs or {})
    labels = {i.target: n for n, i in enumerate(instructions) if i.kind == "label"}
    pc = 0
    def value(token):
        if re.fullmatch(r"[+-]?\d+", token): return int(token)
        try:
            result = float(token)
            if not math.isfinite(result): raise ValueError("Non-finite value")
            return result
        except ValueError:
            return env[token]
    def operation(op, a, b):
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op in ("/", "%"):
            if b == 0: raise ZeroDivisionError()
            if isinstance(a, int) and isinstance(b, int):
                quotient = abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)
                return quotient if op == "/" else a - quotient * b
            if op == "%": raise ValueError("Float modulo")
            return a / b
        if op == "<": return int(a < b)
        if op == ">": return int(a > b)
        if op == "<=": return int(a <= b)
        if op == ">=": return int(a >= b)
        if op == "==": return int(a == b)
        if op == "!=": return int(a != b)
        raise ValueError(op)
    for _ in range(limit):
        if pc >= len(instructions): return None
        ins = instructions[pc]
        if ins.kind == "assign": env[ins.dest] = value(ins.a)
        elif ins.kind == "cast": env[ins.dest] = (int if ins.op == "int" else float)(value(ins.a))
        elif ins.kind == "binop": env[ins.dest] = operation(ins.op, value(ins.a), value(ins.b))
        elif ins.kind == "return": return value(ins.a) if ins.a is not None else None
        elif ins.kind == "goto":
            pc = labels[ins.target]
            continue
        elif ins.kind == "cond" and operation(ins.op, value(ins.a), value(ins.b)):
            pc = labels[ins.target]
            continue
        pc += 1
    raise RuntimeError("Step limit exceeded")
