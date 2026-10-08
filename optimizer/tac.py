from dataclasses import dataclass
from typing import Optional

BINOPS = {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!="}

@dataclass
class Instr:
    kind: str                      # assign | binop | label | goto | cond | return
    dest: Optional[str] = None
    a: Optional[str] = None        # first operand
    op: Optional[str] = None
    b: Optional[str] = None        # second operand
    target: Optional[str] = None   # label name for jumps / label itself

    def __str__(self) -> str:
        if self.kind == "assign":
            return f"{self.dest} = {self.a}"
        if self.kind == "binop":
            return f"{self.dest} = {self.a} {self.op} {self.b}"
        if self.kind == "label":
            return f"{self.target}:"
        if self.kind == "goto":
            return f"goto {self.target}"
        if self.kind == "cond":
            return f"if {self.a} {self.op} {self.b} goto {self.target}"
        if self.kind == "return":
            return "return" + (f" {self.a}" if self.a else "")
        return "?"

def is_int(tok: Optional[str]) -> bool:
    if tok is None:
        return False
    try:
        int(tok)
        return True
    except ValueError:
        return False


class ParseError(Exception):
    pass


def parse(source: str) -> list:
    prog = []
    for n, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        t = line.split()
        if len(t) == 1 and t[0].endswith(":"):
            prog.append(Instr("label", target=t[0][:-1]))
        elif t[0] == "goto" and len(t) == 2:
            prog.append(Instr("goto", target=t[1]))
        elif t[0] == "if" and len(t) == 6 and t[4] == "goto" and t[2] in BINOPS:
            prog.append(Instr("cond", a=t[1], op=t[2], b=t[3], target=t[5]))
        elif t[0] == "return" and len(t) in (1, 2):
            prog.append(Instr("return", a=t[1] if len(t) == 2 else None))
        elif len(t) == 3 and t[1] == "=":
            prog.append(Instr("assign", dest=t[0], a=t[2]))
        elif len(t) == 5 and t[1] == "=" and t[3] in BINOPS:
            prog.append(Instr("binop", dest=t[0], a=t[2], op=t[3], b=t[4]))
        else:
            raise ParseError(f"Line {n}: unrecognised instruction: '{line}'")
    return prog
