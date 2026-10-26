"""Generate TAC with distinct scoped names and explicit numeric conversions."""
from .parser_ast import (Program, DeclStmt, AssignStmt, Block, IfStmt, WhileStmt,
                         ReturnStmt, BinOp, UnaryOp, NumberLit, Var)
from .semantic import analyse
from .diagnostics import CompilationError


class CodeGen:
    def __init__(self, reserved_names=()):
        self._code = []
        self._tmp_counter = 0
        self._label_counter = 0
        self._used_names = set(reserved_names)

    def _new_tmp(self):
        while True:
            name = f"t{self._tmp_counter}"
            self._tmp_counter += 1
            if name not in self._used_names:
                self._used_names.add(name)
                return name

    def _new_label(self):
        while True:
            name = f"L{self._label_counter}"
            self._label_counter += 1
            if name not in self._used_names:
                self._used_names.add(name)
                return name

    def _emit(self, text): self._code.append(text)

    def _assign(self, symbol, expression):
        place = self.gen(expression)
        conversion = symbol.typ + " " if symbol.typ != expression.value_type else ""
        self._emit(f"{symbol.tac_name} = {conversion}{place}")
        return symbol.tac_name

    def _condition(self, expression, target):
        if isinstance(expression, BinOp) and expression.op in ("<", ">", "<=", ">=", "==", "!="):
            left, right = self.gen(expression.left), self.gen(expression.right)
            self._emit(f"if {left} {expression.op} {right} goto {target}")
        else:
            place = self.gen(expression)
            self._emit(f"if {place} != 0 goto {target}")

    def gen(self, node):
        if isinstance(node, (Program, Block)):
            for statement in node.stmts: self.gen(statement)
            return ""
        if isinstance(node, DeclStmt):
            if node.init is not None: self._assign(node.symbol, node.init)
            return node.symbol.tac_name
        if isinstance(node, AssignStmt): return self._assign(node.symbol, node.value)
        if isinstance(node, Var): return node.symbol.tac_name
        if isinstance(node, NumberLit): return node.value
        if isinstance(node, BinOp):
            left, right = self.gen(node.left), self.gen(node.right)
            temporary = self._new_tmp()
            self._emit(f"{temporary} = {left} {node.op} {right}")
            return temporary
        if isinstance(node, UnaryOp):
            place = self.gen(node.operand)
            temporary = self._new_tmp()
            self._emit(f"{temporary} = -1 * {place}")
            return temporary
        if isinstance(node, ReturnStmt):
            place = self.gen(node.value) if node.value is not None else ""
            self._emit("return" + (f" {place}" if place else ""))
            return ""
        if isinstance(node, IfStmt):
            then_label, end_label = self._new_label(), self._new_label()
            self._condition(node.cond, then_label)
            if node.else_block: self.gen(node.else_block)
            self._emit(f"goto {end_label}")
            self._emit(f"{then_label}:")
            self.gen(node.then_block)
            self._emit(f"{end_label}:")
            return ""
        if isinstance(node, WhileStmt):
            start, body, end = self._new_label(), self._new_label(), self._new_label()
            self._emit(f"{start}:")
            self._condition(node.cond, body)
            self._emit(f"goto {end}")
            self._emit(f"{body}:")
            self.gen(node.body)
            self._emit(f"goto {start}")
            self._emit(f"{end}:")
            return ""
        raise TypeError(f"Unknown AST node: {type(node).__name__}")


def generate(ast):
    analyser, text = analyse(ast)
    if any(issue.level == "error" for issue in analyser.issues):
        raise CompilationError("Semantic analysis", text)
    generator = CodeGen(symbol.tac_name for symbol in analyser.symbols)
    generator.gen(ast)
    return generator._code


def tac_lines_to_str(lines): return "\n".join(lines)
