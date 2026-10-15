"""
optimizer/lexer.py  –  Lexer for the simple source language.

Supported tokens:
  INT  FLOAT  ID  ASSIGN  PLUS MINUS STAR SLASH PERCENT
  EQ NEQ LT GT LEQ GEQ
  LPAREN RPAREN LBRACE RBRACE SEMI COMMA
  IF ELSE WHILE RETURN
  NUMBER  (integer literals)
"""

import re
from dataclasses import dataclass
from typing import List


# --------------------------------------------------------------------------- #
#  Token                                                                       #
# --------------------------------------------------------------------------- #

@dataclass
class Token:
    kind: str
    value: str
    line: int

    def __repr__(self):
        return f"Token({self.kind}, {self.value!r}, line={self.line})"


# --------------------------------------------------------------------------- #
#  Token specification                                                         #
# --------------------------------------------------------------------------- #

KEYWORDS = {"if", "else", "while", "return", "int", "float"}

_RULES = [
    ("NUMBER",   r"\d+(\.\d+)?"),
    ("ID",       r"[A-Za-z_]\w*"),
    ("COMMENT",  r"//[^\n]*"),       # must be before SLASH
    ("LEQ",      r"<="),
    ("GEQ",      r">="),
    ("EQ",       r"=="),
    ("NEQ",      r"!="),
    ("LT",       r"<"),
    ("GT",       r">"),
    ("ASSIGN",   r"="),
    ("PLUS",     r"\+"),
    ("MINUS",    r"-"),
    ("STAR",     r"\*"),
    ("SLASH",    r"/"),
    ("PERCENT",  r"%"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("SEMI",     r";"),
    ("COMMA",    r","),
    ("NEWLINE",  r"\n"),
    ("SKIP",     r"[ \t]+"),
    ("MISMATCH", r"."),
]

_MASTER = re.compile(
    "|".join(f"(?P<{name}>{pat})" for name, pat in _RULES)
)


class LexError(Exception):
    pass


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    for mo in _MASTER.finditer(source):
        kind = mo.lastgroup
        value = mo.group()
        if kind == "NEWLINE":
            line += 1
        elif kind in ("SKIP", "COMMENT"):
            pass
        elif kind == "MISMATCH":
            raise LexError(f"Line {line}: unexpected character {value!r}")
        else:
            # Promote keywords
            if kind == "ID" and value in KEYWORDS:
                kind = value.upper()  # e.g. "if" -> "IF"
            tokens.append(Token(kind, value, line))
    tokens.append(Token("EOF", "", line))
    return tokens
