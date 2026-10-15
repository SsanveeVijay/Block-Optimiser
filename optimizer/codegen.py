"""
optimizer/codegen.py  –  Intermediate Code Generation (Three-Address Code).

Walks the AST and emits TAC instructions as strings.
The output is a list of TAC lines compatible with optimizer/tac.py.

Temporary variables:  t0, t1, t2, ...
Labels:               L0, L1, L2, ...
"""

from typing import List
from .parser_ast import (
    ASTNode, Program, DeclStmt, AssignStmt, Block,
    IfStmt, WhileStmt, ReturnStmt, BinOp, UnaryOp, NumberLit, Var
)

# Map AST operator tokens to TAC operators
_OP_MAP = {
    "+": "+", "-": "-", "*": "*", "/": "/", "%": "%",
    "<": "<", ">": ">", "<=": "<=", ">=": ">=", "==": "==", "!=": "!=",
}


class CodeGen:
    def __init__(self):
        self._code: List[str] = []
        self._tmp_counter = 0
        self._label_counter = 0

    # -- helpers -------------------------------------------------------------- #

    def _new_tmp(self) -> str:
        name = f"t{self._tmp_counter}"
        self._tmp_counter += 1
        return name

    def _new_label(self) -> str:
        name = f"L{self._label_counter}"
        self._label_counter += 1
        return name

    def _emit(self, instr: str):
        self._code.append(instr)

    # -- visitors ------------------------------------------------------------- #

    def gen(self, node: ASTNode) -> str:
        """Generate code for node; returns the 'place' holding its value."""
        if isinstance(node, Program):
            return self._gen_program(node)
        if isinstance(node, DeclStmt):
            return self._gen_decl(node)
        if isinstance(node, AssignStmt):
            return self._gen_assign(node)
        if isinstance(node, Block):
            return self._gen_block(node)
        if isinstance(node, IfStmt):
            return self._gen_if(node)
        if isinstance(node, WhileStmt):
            return self._gen_while(node)
        if isinstance(node, ReturnStmt):
            return self._gen_return(node)
        if isinstance(node, BinOp):
            return self._gen_binop(node)
        if isinstance(node, UnaryOp):
            return self._gen_unary(node)
        if isinstance(node, NumberLit):
            return node.value
        if isinstance(node, Var):
            return node.name
        raise NotImplementedError(f"CodeGen: unknown node {type(node).__name__}")

    def _gen_program(self, node: Program) -> str:
        for s in node.stmts:
            self.gen(s)
        return ""

    def _gen_decl(self, node: DeclStmt) -> str:
        if node.init:
            place = self.gen(node.init)
            self._emit(f"{node.name} = {place}")
        return node.name

    def _gen_assign(self, node: AssignStmt) -> str:
        place = self.gen(node.value)
        self._emit(f"{node.name} = {place}")
        return node.name

    def _gen_block(self, node: Block) -> str:
        for s in node.stmts:
            self.gen(s)
        return ""

    def _gen_if(self, node: IfStmt) -> str:
        # Evaluate condition as a binop; fall through to else / end.
        cond = node.cond

        if isinstance(cond, BinOp) and cond.op in _OP_MAP:
            left_place = self.gen(cond.left)
            right_place = self.gen(cond.right)
            then_label = self._new_label()
            end_label = self._new_label()
            op = _OP_MAP[cond.op]
            self._emit(f"if {left_place} {op} {right_place} goto {then_label}")
        else:
            # Treat condition value as truthy (non-zero)
            cond_place = self.gen(cond)
            then_label = self._new_label()
            end_label = self._new_label()
            self._emit(f"if {cond_place} != 0 goto {then_label}")

        # Else branch (or fall-through)
        if node.else_block:
            self._gen_block(node.else_block)
        self._emit(f"goto {end_label}")

        # Then branch
        self._emit(f"{then_label}:")
        self._gen_block(node.then_block)

        self._emit(f"{end_label}:")
        return ""

    def _gen_while(self, node: WhileStmt) -> str:
        start_label = self._new_label()
        body_label = self._new_label()
        end_label = self._new_label()

        self._emit(f"{start_label}:")
        cond = node.cond
        if isinstance(cond, BinOp) and cond.op in _OP_MAP:
            left_place = self.gen(cond.left)
            right_place = self.gen(cond.right)
            op = _OP_MAP[cond.op]
            self._emit(f"if {left_place} {op} {right_place} goto {body_label}")
        else:
            cond_place = self.gen(cond)
            self._emit(f"if {cond_place} != 0 goto {body_label}")

        self._emit(f"goto {end_label}")
        self._emit(f"{body_label}:")
        self._gen_block(node.body)
        self._emit(f"goto {start_label}")
        self._emit(f"{end_label}:")
        return ""

    def _gen_return(self, node: ReturnStmt) -> str:
        if node.value:
            place = self.gen(node.value)
            self._emit(f"return {place}")
        else:
            self._emit("return")
        return ""

    def _gen_binop(self, node: BinOp) -> str:
        left_place = self.gen(node.left)
        right_place = self.gen(node.right)
        op = _OP_MAP[node.op]
        tmp = self._new_tmp()
        self._emit(f"{tmp} = {left_place} {op} {right_place}")
        return tmp

    def _gen_unary(self, node: UnaryOp) -> str:
        operand_place = self.gen(node.operand)
        tmp = self._new_tmp()
        self._emit(f"{tmp} = 0 - {operand_place}")
        return tmp


# --------------------------------------------------------------------------- #
#  Public entry point                                                          #
# --------------------------------------------------------------------------- #

def generate(ast: Program) -> List[str]:
    """Walk AST and return a list of TAC instruction strings."""
    cg = CodeGen()
    cg.gen(ast)
    return cg._code


def tac_lines_to_str(lines: List[str]) -> str:
    return "\n".join(lines)
