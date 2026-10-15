"""
optimizer/parser_ast.py  –  Recursive-descent parser + AST nodes.

Grammar (simplified):
  program     ::= stmt*
  stmt        ::= decl_stmt | assign_stmt | if_stmt | while_stmt | return_stmt | block
  decl_stmt   ::= TYPE ID ( ASSIGN expr )? SEMI
  assign_stmt ::= ID ASSIGN expr SEMI
  if_stmt     ::= IF LPAREN expr RPAREN block ( ELSE block )?
  while_stmt  ::= WHILE LPAREN expr RPAREN block
  return_stmt ::= RETURN expr? SEMI
  block       ::= LBRACE stmt* RBRACE
  expr        ::= cmp
  cmp         ::= add ( RELOP add )*
  add         ::= mul ( (PLUS | MINUS) mul )*
  mul         ::= unary ( (STAR | SLASH | PERCENT) unary )*
  unary       ::= (MINUS)? primary
  primary     ::= NUMBER | ID | LPAREN expr RPAREN
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .lexer import Token, tokenize, LexError


# --------------------------------------------------------------------------- #
#  AST node hierarchy                                                          #
# --------------------------------------------------------------------------- #

class ASTNode:
    pass


# --- Expressions ----------------------------------------------------------- #

@dataclass
class NumberLit(ASTNode):
    value: str          # keep as string; cast in semantic phase
    line: int

@dataclass
class Var(ASTNode):
    name: str
    line: int

@dataclass
class BinOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    line: int

@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode
    line: int


# --- Statements ------------------------------------------------------------ #

@dataclass
class DeclStmt(ASTNode):
    typ: str            # "int" | "float"
    name: str
    init: Optional[ASTNode]
    line: int

@dataclass
class AssignStmt(ASTNode):
    name: str
    value: ASTNode
    line: int

@dataclass
class Block(ASTNode):
    stmts: List[ASTNode] = field(default_factory=list)

@dataclass
class IfStmt(ASTNode):
    cond: ASTNode
    then_block: Block
    else_block: Optional[Block]
    line: int

@dataclass
class WhileStmt(ASTNode):
    cond: ASTNode
    body: Block
    line: int

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode]
    line: int

@dataclass
class Program(ASTNode):
    stmts: List[ASTNode] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Parser                                                                      #
# --------------------------------------------------------------------------- #

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self._tokens = tokens
        self._pos = 0

    # -- helpers -------------------------------------------------------------- #

    def _cur(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset=1) -> Token:
        idx = self._pos + offset
        return self._tokens[idx] if idx < len(self._tokens) else self._tokens[-1]

    def _eat(self, kind: str) -> Token:
        tok = self._cur()
        if tok.kind != kind:
            raise ParseError(
                f"Line {tok.line}: expected {kind!r}, got {tok.kind!r} ({tok.value!r})"
            )
        self._pos += 1
        return tok

    def _match(self, *kinds) -> bool:
        return self._cur().kind in kinds

    # -- top level ------------------------------------------------------------ #

    def parse(self) -> Program:
        prog = Program()
        while not self._match("EOF"):
            prog.stmts.append(self._stmt())
        return prog

    # -- statements ----------------------------------------------------------- #

    def _stmt(self) -> ASTNode:
        tok = self._cur()
        if tok.kind in ("INT", "FLOAT"):
            return self._decl_stmt()
        if tok.kind == "IF":
            return self._if_stmt()
        if tok.kind == "WHILE":
            return self._while_stmt()
        if tok.kind == "RETURN":
            return self._return_stmt()
        if tok.kind == "LBRACE":
            return self._block()
        if tok.kind == "ID":
            return self._assign_stmt()
        raise ParseError(f"Line {tok.line}: unexpected token {tok.kind!r} ({tok.value!r})")

    def _decl_stmt(self) -> DeclStmt:
        typ_tok = self._cur()
        self._pos += 1          # consume INT / FLOAT
        name_tok = self._eat("ID")
        init = None
        if self._match("ASSIGN"):
            self._pos += 1
            init = self._expr()
        self._eat("SEMI")
        return DeclStmt(typ_tok.value, name_tok.value, init, typ_tok.line)

    def _assign_stmt(self) -> AssignStmt:
        name_tok = self._eat("ID")
        self._eat("ASSIGN")
        val = self._expr()
        self._eat("SEMI")
        return AssignStmt(name_tok.value, val, name_tok.line)

    def _if_stmt(self) -> IfStmt:
        tok = self._eat("IF")
        self._eat("LPAREN")
        cond = self._expr()
        self._eat("RPAREN")
        then_b = self._block()
        else_b = None
        if self._match("ELSE"):
            self._pos += 1
            else_b = self._block()
        return IfStmt(cond, then_b, else_b, tok.line)

    def _while_stmt(self) -> WhileStmt:
        tok = self._eat("WHILE")
        self._eat("LPAREN")
        cond = self._expr()
        self._eat("RPAREN")
        body = self._block()
        return WhileStmt(cond, body, tok.line)

    def _return_stmt(self) -> ReturnStmt:
        tok = self._eat("RETURN")
        val = None
        if not self._match("SEMI"):
            val = self._expr()
        self._eat("SEMI")
        return ReturnStmt(val, tok.line)

    def _block(self) -> Block:
        self._eat("LBRACE")
        stmts = []
        while not self._match("RBRACE", "EOF"):
            stmts.append(self._stmt())
        self._eat("RBRACE")
        return Block(stmts)

    # -- expressions ---------------------------------------------------------- #

    _RELOPS = {"LT", "GT", "LEQ", "GEQ", "EQ", "NEQ"}

    def _expr(self) -> ASTNode:
        return self._cmp()

    def _cmp(self) -> ASTNode:
        node = self._add()
        while self._match(*self._RELOPS):
            op_tok = self._cur()
            self._pos += 1
            right = self._add()
            node = BinOp(op_tok.value, node, right, op_tok.line)
        return node

    def _add(self) -> ASTNode:
        node = self._mul()
        while self._match("PLUS", "MINUS"):
            op_tok = self._cur()
            self._pos += 1
            right = self._mul()
            node = BinOp(op_tok.value, node, right, op_tok.line)
        return node

    def _mul(self) -> ASTNode:
        node = self._unary()
        while self._match("STAR", "SLASH", "PERCENT"):
            op_tok = self._cur()
            self._pos += 1
            right = self._unary()
            node = BinOp(op_tok.value, node, right, op_tok.line)
        return node

    def _unary(self) -> ASTNode:
        if self._match("MINUS"):
            tok = self._cur()
            self._pos += 1
            return UnaryOp("-", self._primary(), tok.line)
        return self._primary()

    def _primary(self) -> ASTNode:
        tok = self._cur()
        if tok.kind == "NUMBER":
            self._pos += 1
            return NumberLit(tok.value, tok.line)
        if tok.kind == "ID":
            self._pos += 1
            return Var(tok.name if hasattr(tok, "name") else tok.value, tok.line)
        if tok.kind == "LPAREN":
            self._pos += 1
            node = self._expr()
            self._eat("RPAREN")
            return node
        raise ParseError(f"Line {tok.line}: expected expression, got {tok.kind!r}")


# --------------------------------------------------------------------------- #
#  Public entry point                                                          #
# --------------------------------------------------------------------------- #

def parse_source(source: str) -> Program:
    """Lex + parse source text; returns a Program AST."""
    tokens = tokenize(source)
    return Parser(tokens).parse()


def ast_to_str(node: ASTNode, indent: int = 0) -> str:
    """Pretty-print an AST for display."""
    pad = "  " * indent
    if isinstance(node, Program):
        body = "\n".join(ast_to_str(s, indent + 1) for s in node.stmts)
        return f"{pad}Program\n{body}"
    if isinstance(node, DeclStmt):
        init = f" = {ast_to_str(node.init, 0)}" if node.init else ""
        return f"{pad}Decl {node.typ} {node.name}{init}"
    if isinstance(node, AssignStmt):
        return f"{pad}Assign {node.name} = {ast_to_str(node.value, 0)}"
    if isinstance(node, IfStmt):
        cond = ast_to_str(node.cond, 0)
        then_ = ast_to_str(node.then_block, indent + 1)
        else_ = ("\n" + pad + "Else\n" + ast_to_str(node.else_block, indent + 1)) if node.else_block else ""
        return f"{pad}If ({cond})\n{then_}{else_}"
    if isinstance(node, WhileStmt):
        cond = ast_to_str(node.cond, 0)
        body = ast_to_str(node.body, indent + 1)
        return f"{pad}While ({cond})\n{body}"
    if isinstance(node, ReturnStmt):
        val = f" {ast_to_str(node.value, 0)}" if node.value else ""
        return f"{pad}Return{val}"
    if isinstance(node, Block):
        body = "\n".join(ast_to_str(s, indent + 1) for s in node.stmts)
        return f"{pad}Block\n{body}" if body else f"{pad}Block (empty)"
    if isinstance(node, BinOp):
        l = ast_to_str(node.left, 0)
        r = ast_to_str(node.right, 0)
        return f"({l} {node.op} {r})"
    if isinstance(node, UnaryOp):
        return f"({node.op}{ast_to_str(node.operand, 0)})"
    if isinstance(node, NumberLit):
        return node.value
    if isinstance(node, Var):
        return node.name
    return repr(node)
