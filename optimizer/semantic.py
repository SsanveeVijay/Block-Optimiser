"""
optimizer/semantic.py  –  Semantic analysis pass.

Checks performed:
  1. Variable declared before use
  2. Variable not declared twice in the same scope
  3. Type consistency (int vs float) – warns on mixed arithmetic

Returns a SymbolTable and a list of SemanticError / SemanticWarning messages.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .parser_ast import (
    ASTNode, Program, DeclStmt, AssignStmt, Block,
    IfStmt, WhileStmt, ReturnStmt, BinOp, UnaryOp, NumberLit, Var
)


# --------------------------------------------------------------------------- #
#  Symbol table                                                                #
# --------------------------------------------------------------------------- #

@dataclass
class Symbol:
    name: str
    typ: str            # "int" | "float" | "unknown"
    declared_line: int


class Scope:
    def __init__(self, parent: Optional["Scope"] = None):
        self._table: Dict[str, Symbol] = {}
        self.parent = parent

    def declare(self, sym: Symbol):
        self._table[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self._table:
            return self._table[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def local_lookup(self, name: str) -> Optional[Symbol]:
        return self._table.get(name)

    def all_symbols(self) -> List[Symbol]:
        return list(self._table.values())


# --------------------------------------------------------------------------- #
#  Semantic analyser                                                           #
# --------------------------------------------------------------------------- #

@dataclass
class SemanticIssue:
    level: str          # "error" | "warning"
    message: str
    line: int

    def __str__(self):
        return f"[{self.level.upper()}] Line {self.line}: {self.message}"


class SemanticAnalyser:
    def __init__(self):
        self.issues: List[SemanticIssue] = []
        self._scope = Scope()           # global scope

    # -- helpers -------------------------------------------------------------- #

    def _error(self, msg: str, line: int):
        self.issues.append(SemanticIssue("error", msg, line))

    def _warn(self, msg: str, line: int):
        self.issues.append(SemanticIssue("warning", msg, line))

    def _push(self):
        self._scope = Scope(self._scope)

    def _pop(self):
        self._scope = self._scope.parent

    # -- visitors ------------------------------------------------------------- #

    def analyse(self, node: ASTNode) -> str:
        """Dispatch to the right visitor; returns inferred type string."""
        if isinstance(node, Program):
            return self._visit_program(node)
        if isinstance(node, DeclStmt):
            return self._visit_decl(node)
        if isinstance(node, AssignStmt):
            return self._visit_assign(node)
        if isinstance(node, Block):
            return self._visit_block(node)
        if isinstance(node, IfStmt):
            return self._visit_if(node)
        if isinstance(node, WhileStmt):
            return self._visit_while(node)
        if isinstance(node, ReturnStmt):
            return self._visit_return(node)
        if isinstance(node, BinOp):
            return self._visit_binop(node)
        if isinstance(node, UnaryOp):
            return self.analyse(node.operand)
        if isinstance(node, NumberLit):
            return "float" if "." in node.value else "int"
        if isinstance(node, Var):
            return self._visit_var(node)
        return "unknown"

    def _visit_program(self, node: Program) -> str:
        for s in node.stmts:
            self.analyse(s)
        return "void"

    def _visit_decl(self, node: DeclStmt) -> str:
        if self._scope.local_lookup(node.name):
            self._error(f"Variable '{node.name}' already declared in this scope", node.line)
        else:
            sym = Symbol(node.name, node.typ, node.line)
            self._scope.declare(sym)
        if node.init:
            init_type = self.analyse(node.init)
            if init_type not in (node.typ, "unknown"):
                self._warn(
                    f"Assigning {init_type!r} to '{node.name}' declared as {node.typ!r}",
                    node.line,
                )
        return node.typ

    def _visit_assign(self, node: AssignStmt) -> str:
        sym = self._scope.lookup(node.name)
        if not sym:
            self._error(f"Variable '{node.name}' used before declaration", node.line)
        val_type = self.analyse(node.value)
        if sym and val_type not in (sym.typ, "unknown"):
            self._warn(
                f"Assigning {val_type!r} to '{node.name}' declared as {sym.typ!r}",
                node.line,
            )
        return val_type

    def _visit_block(self, node: Block) -> str:
        self._push()
        for s in node.stmts:
            self.analyse(s)
        self._pop()
        return "void"

    def _visit_if(self, node: IfStmt) -> str:
        self.analyse(node.cond)
        self._visit_block(node.then_block)
        if node.else_block:
            self._visit_block(node.else_block)
        return "void"

    def _visit_while(self, node: WhileStmt) -> str:
        self.analyse(node.cond)
        self._visit_block(node.body)
        return "void"

    def _visit_return(self, node: ReturnStmt) -> str:
        if node.value:
            return self.analyse(node.value)
        return "void"

    def _visit_binop(self, node: BinOp) -> str:
        lt = self.analyse(node.left)
        rt = self.analyse(node.right)
        if lt != rt and "unknown" not in (lt, rt):
            self._warn(
                f"Mixed types in expression: {lt!r} {node.op} {rt!r}",
                node.line,
            )
        return "float" if "float" in (lt, rt) else lt

    def _visit_var(self, node: Var) -> str:
        sym = self._scope.lookup(node.name)
        if not sym:
            self._error(f"Variable '{node.name}' used before declaration", node.line)
            return "unknown"
        return sym.typ


# --------------------------------------------------------------------------- #
#  Public entry point                                                          #
# --------------------------------------------------------------------------- #

def analyse(ast: Program):
    """
    Run semantic analysis on the AST.
    Returns (analyser, issues_text).
    """
    sa = SemanticAnalyser()
    sa.analyse(ast)
    if sa.issues:
        text = "\n".join(str(i) for i in sa.issues)
    else:
        text = "No semantic errors found."
    return sa, text
