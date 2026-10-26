"""Unbounded integers, C-style integer division/modulo, and finite floats."""

import math
import re

NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def number(text):
    if text is None or not NUMBER.fullmatch(text):
        raise ValueError(f"Invalid numeric literal: {text!r}")
    value = float(text) if any(c in text for c in ".eE") else int(text)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Numeric literal must be finite")
    return value


def is_number(text):
    try:
        number(text)
        return True
    except ValueError:
        return False


def evaluate(op, x, y):
    if op == "+":
        result = x + y
    elif op == "-":
        result = x - y
    elif op == "*":
        result = x * y
    elif op in ("/", "%"):
        if y == 0:
            raise ZeroDivisionError("Division or modulo by zero")
        if isinstance(x, int) and isinstance(y, int):
            q = abs(x) // abs(y)
            q = q if (x >= 0) == (y >= 0) else -q
            result = q if op == "/" else x - q * y
        elif op == "/":
            result = x / y
        else:
            raise ValueError("Modulo requires integer operands")
    else:
        comparisons = {"<": x < y, ">": x > y, "<=": x <= y,
                       ">=": x >= y, "==": x == y, "!=": x != y}
        result = int(comparisons[op])
    if isinstance(result, float) and not math.isfinite(result):
        raise OverflowError("Floating-point result is not finite")
    return result
