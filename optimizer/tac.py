"""Validated three-address code with source-line metadata."""
import re
from dataclasses import dataclass
from typing import Optional
from .diagnostics import CompilationError
from .numeric import is_number, number

BINOPS = {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!="}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")

@dataclass
class Instr:
    kind: str
    dest: Optional[str] = None
    a: Optional[str] = None
    op: Optional[str] = None
    b: Optional[str] = None
    target: Optional[str] = None
    line: Optional[int] = None

    def __str__(self):
        if self.kind == "assign": return f"{self.dest} = {self.a}"
        if self.kind == "binop": return f"{self.dest} = {self.a} {self.op} {self.b}"
        if self.kind == "cast": return f"{self.dest} = {self.op} {self.a}"
        if self.kind == "label": return f"{self.target}:"
        if self.kind == "goto": return f"goto {self.target}"
        if self.kind == "cond": return f"if {self.a} {self.op} {self.b} goto {self.target}"
        if self.kind == "return": return "return" + (f" {self.a}" if self.a is not None else "")
        raise ValueError(f"Unknown instruction kind {self.kind!r}")


def is_int(token):
    return is_number(token) and isinstance(number(token), int)


class ParseError(CompilationError):
    def __init__(self, message, line=None):
        super().__init__("TAC parsing", message, line)


def parse(source):
    program, labels = [], set()
    def identifier(value):
        return bool(IDENTIFIER.fullmatch(value))
    def operand(value):
        return identifier(value) or is_number(value)
    for line_number, raw in enumerate(source.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        t = line.split()
        ins = None
        if len(t) == 1 and t[0].endswith(":") and identifier(t[0][:-1]):
            label = t[0][:-1]
            if label in labels:
                raise ParseError(f"Duplicate label {label!r}", line_number)
            labels.add(label)
            ins = Instr("label", target=label)
        elif len(t) == 2 and t[0] == "goto" and identifier(t[1]):
            ins = Instr("goto", target=t[1])
        elif (len(t) == 6 and t[0] == "if" and t[4] == "goto"
              and t[2] in BINOPS and operand(t[1]) and operand(t[3]) and identifier(t[5])):
            ins = Instr("cond", a=t[1], op=t[2], b=t[3], target=t[5])
        elif (len(t) == 4 and t[0] == "if" and t[2] == "goto"
              and operand(t[1]) and identifier(t[3])):
            ins = Instr("cond", a=t[1], op="!=", b="0", target=t[3])
        elif t[0] == "return" and (len(t) == 1 or len(t) == 2 and operand(t[1])):
            ins = Instr("return", a=t[1] if len(t) == 2 else None)
        elif len(t) >= 3 and identifier(t[0]) and t[1] == "=":
            if len(t) == 3 and operand(t[2]):
                ins = Instr("assign", dest=t[0], a=t[2])
            elif len(t) == 4 and t[2] in ("int", "float") and operand(t[3]):
                ins = Instr("cast", dest=t[0], op=t[2], a=t[3])
            elif len(t) == 5 and operand(t[2]) and t[3] in BINOPS and operand(t[4]):
                ins = Instr("binop", dest=t[0], a=t[2], op=t[3], b=t[4])
        if ins is None:
            raise ParseError(f"Unrecognised instruction: {line!r}", line_number)
        if ins.op == "%" and any(is_number(value) and not is_int(value) for value in (ins.a, ins.b)):
            raise ParseError("Modulo requires integer operands", line_number)
        ins.line = line_number
        program.append(ins)
    return program
