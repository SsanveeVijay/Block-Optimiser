"""
tests/test_full_pipeline.py  –  Tests for the full compiler pipeline.
Covers: lexer, parser, semantic analysis, codegen, algebraic simplification, CSE.
"""

import os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from optimizer.lexer import tokenize, LexError
from optimizer.parser_ast import parse_source, ast_to_str, ParseError, Program
from optimizer.semantic import analyse
from optimizer.codegen import generate, tac_lines_to_str
from optimizer.pipeline import run, run_source
from optimizer.algebraic_simplification import simplify_all
from optimizer.cse import cse_all
from optimizer.tac import parse
from optimizer.basic_blocks import build_blocks


# --------------------------------------------------------------------------- #
#  Lexer tests                                                                 #
# --------------------------------------------------------------------------- #

class TestLexer(unittest.TestCase):
    def test_basic_tokens(self):
        tokens = tokenize("int x = 5 + 3;")
        kinds = [t.kind for t in tokens]
        self.assertIn("INT", kinds)
        self.assertIn("ID", kinds)
        self.assertIn("NUMBER", kinds)
        self.assertIn("PLUS", kinds)
        self.assertIn("SEMI", kinds)

    def test_keywords_recognised(self):
        tokens = tokenize("if while return")
        kinds = [t.kind for t in tokens if t.kind != "EOF"]
        self.assertEqual(kinds, ["IF", "WHILE", "RETURN"])

    def test_relational_ops(self):
        tokens = tokenize("<= >= == !=")
        kinds = [t.kind for t in tokens if t.kind != "EOF"]
        self.assertEqual(kinds, ["LEQ", "GEQ", "EQ", "NEQ"])

    def test_lex_error(self):
        with self.assertRaises(LexError):
            tokenize("int x = @bad;")


# --------------------------------------------------------------------------- #
#  Parser / AST tests                                                          #
# --------------------------------------------------------------------------- #

class TestParser(unittest.TestCase):
    def test_decl_and_assign(self):
        ast = parse_source("int x = 5; x = x + 1;")
        self.assertIsInstance(ast, Program)
        self.assertEqual(len(ast.stmts), 2)

    def test_if_else(self):
        src = "int x = 1; if (x > 0) { int y = 2; } else { int y = 3; }"
        ast = parse_source(src)
        self.assertEqual(len(ast.stmts), 2)  # decl + if

    def test_while_loop(self):
        src = "int i = 0; while (i < 10) { i = i + 1; }"
        ast = parse_source(src)
        self.assertEqual(len(ast.stmts), 2)

    def test_return(self):
        ast = parse_source("int x = 42; return x;")
        self.assertEqual(len(ast.stmts), 2)

    def test_ast_text_nonempty(self):
        ast = parse_source("int a = 1 + 2;")
        text = ast_to_str(ast)
        self.assertIn("Program", text)
        self.assertIn("Decl", text)


# --------------------------------------------------------------------------- #
#  Semantic analysis tests                                                     #
# --------------------------------------------------------------------------- #

class TestSemantic(unittest.TestCase):
    def test_undeclared_variable(self):
        ast = parse_source("x = 5;")
        _, text = analyse(ast)
        self.assertIn("ERROR", text)
        self.assertIn("before declaration", text)

    def test_double_declaration(self):
        ast = parse_source("int x = 1; int x = 2;")
        _, text = analyse(ast)
        self.assertIn("ERROR", text)
        self.assertIn("already declared", text)

    def test_no_errors_clean_program(self):
        ast = parse_source("int a = 1; int b = a + 2; return b;")
        _, text = analyse(ast)
        self.assertIn("No semantic errors", text)

    def test_type_warning_mixed(self):
        # Assigning float literal to int variable should warn
        ast = parse_source("int x = 3.14;")
        _, text = analyse(ast)
        self.assertIn("WARNING", text)


# --------------------------------------------------------------------------- #
#  Code generation tests                                                       #
# --------------------------------------------------------------------------- #

class TestCodeGen(unittest.TestCase):
    def test_simple_arithmetic(self):
        ast = parse_source("int a = 2 + 3; return a;")
        lines = generate(ast)
        tac = "\n".join(lines)
        self.assertIn("2 + 3", tac)
        self.assertIn("return", tac)

    def test_while_produces_labels(self):
        ast = parse_source("int i = 0; while (i < 5) { i = i + 1; }")
        lines = generate(ast)
        tac = "\n".join(lines)
        self.assertIn("goto", tac)
        self.assertIn("if", tac)

    def test_if_else_produces_labels(self):
        ast = parse_source("int x = 1; if (x > 0) { int y = 1; } else { int y = 0; }")
        lines = generate(ast)
        tac = "\n".join(lines)
        self.assertIn("goto", tac)


# --------------------------------------------------------------------------- #
#  Algebraic simplification tests                                             #
# --------------------------------------------------------------------------- #

class TestAlgebraicSimplification(unittest.TestCase):
    def _run_simpl(self, src):
        prog = parse(src)
        blocks = build_blocks(prog)
        simplified, log = simplify_all(blocks)
        text = "\n".join(str(i) for b in simplified for i in b.instrs)
        return text, log

    def test_add_zero(self):
        text, log = self._run_simpl("a = x + 0\nreturn a\n")
        self.assertIn("a = x", text)

    def test_mul_one(self):
        text, log = self._run_simpl("a = x * 1\nreturn a\n")
        self.assertIn("a = x", text)

    def test_mul_zero(self):
        text, log = self._run_simpl("a = x * 0\nreturn a\n")
        self.assertIn("a = 0", text)

    def test_sub_self(self):
        text, log = self._run_simpl("a = x - x\nreturn a\n")
        self.assertIn("a = 0", text)


# --------------------------------------------------------------------------- #
#  CSE tests                                                                   #
# --------------------------------------------------------------------------- #

class TestCSE(unittest.TestCase):
    def _run_cse(self, src):
        prog = parse(src)
        blocks = build_blocks(prog)
        cse_blocks, log = cse_all(blocks)
        return cse_blocks, log

    def test_cse_eliminates_duplicate(self):
        src = "t1 = a + b\nt2 = a + b\nreturn t2\n"
        blocks, log = self._run_cse(src)
        changes = [c for ch in log.values() for c in ch]
        self.assertTrue(any("CSE" in c for c in changes))

    def test_cse_no_false_elimination_after_redef(self):
        src = "t1 = a + b\na = 5\nt2 = a + b\nreturn t2\n"
        blocks, log = self._run_cse(src)
        # After a is redefined, t2 = a + b should NOT be eliminated
        changes = [c for ch in log.values() for c in ch]
        self.assertFalse(any("CSE" in c for c in changes))


# --------------------------------------------------------------------------- #
#  Full end-to-end pipeline test                                               #
# --------------------------------------------------------------------------- #

class TestFullPipeline(unittest.TestCase):
    _src = """
int a = 2 + 3;
int b = a * 4;
int i = 0;
while (i < 10) {
    int t = b + i;
    i = i + 1;
}
return i;
"""

    def test_run_source_keys(self):
        res = run_source(self._src)
        for key in ("ast_text", "semantic_text", "tac_text",
                    "blocks_text", "cfg_text", "folded_text",
                    "simplified_text", "optimised_text", "log_text"):
            self.assertIn(key, res, f"Missing key: {key}")

    def test_run_source_constant_folded(self):
        res = run_source("int a = 2 + 3; int b = a * 4; return b;")
        # 2 + 3 = 5, 5 * 4 = 20
        self.assertIn("20", res["folded_text"])

    def test_sample_src_file(self):
        path = os.path.join(ROOT, "samples", "sample_source.src")
        if os.path.exists(path):
            with open(path) as f:
                res = run_source(f.read())
            self.assertIn("Program", res["ast_text"])

    def test_tac_pipeline_unchanged(self):
        """Ensure legacy TAC pipeline still works correctly."""
        r = run("a = 2 + 3\nb = a * 4\nreturn b\n")
        self.assertIn("20", r["folded_text"])


if __name__ == "__main__":
    unittest.main()
