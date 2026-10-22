"""Source lexer with positions, comments and actionable diagnostics."""
import re
from dataclasses import dataclass
from .diagnostics import CompilationError
from .numeric import number

@dataclass
class Token:
    kind: str
    value: str
    line: int
    column: int = 1

KEYWORDS = {"if", "else", "while", "return", "int", "float"}
_RULES = [
    ("NUMBER", r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"),
    ("ID", r"[A-Za-z_][A-Za-z_0-9]*"),
    ("COMMENT", r"//[^\n]*"),
    ("BLOCK_COMMENT", r"/\*[\s\S]*?\*/"),
    ("UNCLOSED_COMMENT", r"/\*[\s\S]*\Z"),
    ("LEQ", r"<="), ("GEQ", r">="), ("EQ", r"=="), ("NEQ", r"!="),
    ("LT", r"<"), ("GT", r">"), ("ASSIGN", r"="),
    ("PLUS", r"\+"), ("MINUS", r"-"), ("STAR", r"\*"),
    ("SLASH", r"/"), ("PERCENT", r"%"),
    ("LPAREN", r"\("), ("RPAREN", r"\)"),
    ("LBRACE", r"\{"), ("RBRACE", r"\}"),
    ("SEMI", r";"), ("COMMA", r","),
    ("SPACE", r"\s+"), ("MISMATCH", r"."),
]
_MASTER = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _RULES))

class LexError(CompilationError):
    def __init__(self, message, line=None, column=None, tokens=None):
        super().__init__("Lexical analysis", message, line, column,
                         {"tokens": tokens or [], "tokens_text": format_tokens(tokens or [])})

def format_tokens(tokens):
    return "Line:Col  Token          Value\n" + "\n".join(
        f"{t.line:>4}:{t.column:<4} {t.kind:<14} {t.value!r}" for t in tokens)

def tokenize(source):
    tokens = []
    line, line_start = 1, 0
    for match in _MASTER.finditer(source):
        kind, value = match.lastgroup, match.group()
        column = match.start() - line_start + 1
        if kind in ("MISMATCH", "UNCLOSED_COMMENT"):
            message = ("Unterminated block comment; expected '*/'" if kind == "UNCLOSED_COMMENT"
                       else f"Unexpected character {value!r}")
            raise LexError(message, line, column, tokens)
        if kind not in ("SPACE", "COMMENT", "BLOCK_COMMENT"):
            if kind == "NUMBER":
                try:
                    number(value)
                except ValueError as error:
                    raise LexError(str(error), line, column, tokens) from error
            if kind == "ID" and value in KEYWORDS:
                kind = value.upper()
            tokens.append(Token(kind, value, line, column))
        if "\n" in value:
            line += value.count("\n")
            line_start = match.start() + value.rfind("\n") + 1
    tokens.append(Token("EOF", "", line, len(source) - line_start + 1))
    return tokens
