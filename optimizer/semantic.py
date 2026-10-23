"""Scope resolution, numeric type checks and conservative definite assignment."""
from dataclasses import dataclass
from .parser_ast import (Program, DeclStmt, AssignStmt, Block, IfStmt, WhileStmt,
                         ReturnStmt, BinOp, UnaryOp, NumberLit, Var)
from .numeric import evaluate, number

@dataclass
class Symbol:
    name: str
    typ: str
    declared_line: int
    tac_name: str = ""

class Scope:
    def __init__(self, parent=None):
        self._table = {}
        self.parent = parent
    def declare(self, symbol): self._table[symbol.name] = symbol
    def local_lookup(self, name): return self._table.get(name)
    def lookup(self, name):
        return self.local_lookup(name) or (self.parent.lookup(name) if self.parent else None)
    def all_symbols(self): return list(self._table.values())

@dataclass
class SemanticIssue:
    level: str
    message: str
    line: int
    def __str__(self):
        return f"[{self.level.upper()}] Line {self.line}: {self.message}"


def constant_value(node):
    """Evaluate literal-only expressions; variables are deliberately unknown."""
    if isinstance(node, NumberLit): return number(node.value)
    if isinstance(node, UnaryOp): return -constant_value(node.operand)
    if isinstance(node, BinOp):
        return evaluate(node.op, constant_value(node.left), constant_value(node.right))
    raise ValueError("Not a constant expression")


class SemanticAnalyser:
    def __init__(self, source_names=()):
        self.issues = []
        self.symbols = []
        self._scope = Scope()
        self._initialized = set()
        self._source_names = set(source_names)
        self._used_tac_names = set()

    def _tac_name(self, name):
        # Keep the source spelling when it is unique. Only shadowed or repeated
        # declarations need a suffix, which must not collide with a source name.
        if name not in self._used_tac_names:
            result = name
        else:
            suffix = 1
            while (candidate := f"{name}{suffix}") in self._source_names | self._used_tac_names:
                suffix += 1
            result = candidate
        self._used_tac_names.add(result)
        return result

    def _error(self, message, line): self.issues.append(SemanticIssue("error", message, line))
    def _warn(self, message, line): self.issues.append(SemanticIssue("warning", message, line))

    def analyse(self, node):
        typ = self._visit(node)
        node.value_type = typ
        return typ

    def _assignment_type(self, expected, actual, name, line):
        if actual not in (expected, "unknown"):
            self._warn(f"Assigning {actual!r} to '{name}' declared as {expected!r}; "
                       + ("conversion truncates toward zero" if expected == "int" else "converted to float"), line)

    def _visit(self, node):
        if isinstance(node, Program):
            for statement in node.stmts: self.analyse(statement)
            return "void"
        if isinstance(node, DeclStmt):
            symbol = self._scope.local_lookup(node.name)
            if symbol:
                self._error(f"Variable '{node.name}' already declared in this scope", node.line)
            else:
                symbol = Symbol(node.name, node.typ, node.line, self._tac_name(node.name))
                self.symbols.append(symbol)
                self._scope.declare(symbol)
            node.symbol = symbol
            if node.init is not None:
                typ = self.analyse(node.init)
                self._assignment_type(node.typ, typ, node.name, node.line)
                self._initialized.add(symbol.tac_name)
            return node.typ
        if isinstance(node, AssignStmt):
            symbol = self._scope.lookup(node.name)
            node.symbol = symbol
            if not symbol:
                self._error(f"Variable '{node.name}' used before declaration", node.line)
            typ = self.analyse(node.value)
            if symbol:
                self._assignment_type(symbol.typ, typ, node.name, node.line)
                self._initialized.add(symbol.tac_name)
            return typ
        if isinstance(node, Block):
            parent = self._scope
            self._scope = Scope(parent)
            for statement in node.stmts: self.analyse(statement)
            self._scope = parent
            return "void"
        if isinstance(node, IfStmt):
            self.analyse(node.cond)
            before = self._initialized.copy()
            self.analyse(node.then_block)
            then = self._initialized.copy()
            self._initialized = before.copy()
            if node.else_block: self.analyse(node.else_block)
            self._initialized &= then
            return "void"
        if isinstance(node, WhileStmt):
            self.analyse(node.cond)
            before = self._initialized.copy()
            self.analyse(node.body)
            self._initialized = before
            return "void"
        if isinstance(node, ReturnStmt):
            return self.analyse(node.value) if node.value is not None else "void"
        if isinstance(node, NumberLit):
            return "float" if isinstance(number(node.value), float) else "int"
        if isinstance(node, Var):
            symbol = self._scope.lookup(node.name)
            node.symbol = symbol
            if not symbol:
                self._error(f"Variable '{node.name}' used before declaration", node.line)
                return "unknown"
            if symbol.tac_name not in self._initialized:
                self._error(f"Variable '{node.name}' may be used before initialization", node.line)
            return symbol.typ
        if isinstance(node, UnaryOp): return self.analyse(node.operand)
        if isinstance(node, BinOp):
            left, right = self.analyse(node.left), self.analyse(node.right)
            if node.op == "%" and "float" in (left, right):
                self._error("Modulo requires integer operands", node.line)
            if node.op in ("/", "%"):
                try:
                    if constant_value(node.right) == 0:
                        self._error("Division or modulo by constant zero", node.line)
                except (ValueError, ArithmeticError):
                    pass
            if left != right and "unknown" not in (left, right):
                self._warn(f"Mixed types in expression: {left!r} {node.op} {right!r}", node.line)
            if node.op in ("<", ">", "<=", ">=", "==", "!="): return "int"
            return "float" if "float" in (left, right) else left
        return "unknown"


def _declared_names(node):
    if isinstance(node, DeclStmt):
        return {node.name}
    if isinstance(node, (Program, Block)):
        return set().union(*(_declared_names(statement) for statement in node.stmts))
    if isinstance(node, IfStmt):
        return _declared_names(node.then_block) | (_declared_names(node.else_block) if node.else_block else set())
    if isinstance(node, WhileStmt):
        return _declared_names(node.body)
    return set()


def analyse(ast):
    analyser = SemanticAnalyser(_declared_names(ast))
    analyser.analyse(ast)
    text = "\n".join(str(issue) for issue in analyser.issues) or "No semantic errors found."
    return analyser, text
