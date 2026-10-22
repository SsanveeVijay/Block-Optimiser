"""Regression cases for correctness, diagnostics, optimization and CLI behavior."""
import contextlib
import io
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from optimizer.diagnostics import CompilationError
from optimizer.lexer import tokenize, LexError
from optimizer.parser_ast import ParseError
from optimizer.pipeline import run, run_source
from optimizer.tac import parse
from optimizer.cse import cse_all
from optimizer.basic_blocks import build_blocks
from tac_runner import execute

ROOT = Path(__file__).resolve().parents[1]


def flatten(blocks): return [i for b in blocks for i in b.instrs]


class BehaviorTests(unittest.TestCase):
    def check_source(self, source, expected):
        result = run_source(source)
        self.assertEqual(execute(parse(result["tac_text"])), expected)
        for key in ("folded", "simplified", "cse_blocks", "optimised"):
            self.assertEqual(execute(flatten(result[key])), expected, key)
        return result

    def test_shadowing_and_generated_names(self):
        self.check_source("int t0 = 10; int __t0 = 5; int x = 1; "
                          "{ int x = 2; t0 = t0 + x; } return t0 + x + __t0;", 18)

    def test_shadow_initializer_sees_uninitialized_inner(self):
        with self.assertRaises(CompilationError):
            run_source("int x = 1; { int x = x + 1; }")

    def test_arithmetic_condition_uses_integer_division(self):
        self.check_source("if (1 / 2) { return 10; } else { return 20; }", 20)
        self.check_source("int i = 0; while (2 - i) { i = i + 1; } return i;", 2)

    def test_equality_precedence(self):
        self.check_source("return 0 == 2 < 1;", 1)

    def test_repeated_unary_minus(self):
        self.check_source("return ---7;", -7)

    def test_loop_and_nested_if(self):
        self.check_source("int i=0; int sum=0; while(i<6) { "
                          "if(i<3) { sum=sum+i; } else { sum=sum+2; } i=i+1; } return sum;", 9)

    def test_float_conversions(self):
        r = self.check_source("float x = 5; int y = -3.8; return x / 2 + y;", -0.5)
        self.assertIn("WARNING", r["semantic_text"])
        self.assertTrue(any(i.kind == "cast" for i in parse(r["tac_text"])))

    def test_numeric_comparison_result_is_int(self):
        self.check_source("float x=2.5; int yes=x>2; return yes / 2;", 0)

    def test_float_literal_without_declaration(self):
        r = self.check_source("return 0.0 + -0.0;", 0.0)
        self.assertIn("skipped", r["diagnostics_text"])

    def test_signed_float_zero_preserved(self):
        r = run_source("float x=0.0; return -x;")
        for key in ("folded", "simplified", "cse_blocks", "optimised"):
            self.assertEqual(math.copysign(1, execute(flatten(r[key]))), -1)

    def test_integer_division_modulo_and_large_values(self):
        self.check_source("return -7 / 2 * 10 + -7 % 2;", -31)
        self.check_source("return 100000000000000000000000000001 / 3;", 33333333333333333333333333333)

    def test_early_return_removes_unreachable_blocks(self):
        r = self.check_source("return 7; int x=2; return x;", 7)
        self.assertLess(len(flatten(r["optimised"])), len(flatten(r["blocks"])))

    def test_branch_true_false_and_final_targets(self):
        for condition, expected in (("2 > 0", 1), ("2 < 0", 2)):
            r = run(f"if {condition} goto YES\nreturn 2\nYES:\nreturn 1")
            self.assertEqual(execute(flatten(r["optimised"])), expected)
            self.assertFalse(r["final_cfg"].unreachable())
            self.assertFalse(any(i.kind == "cond" for i in flatten(r["optimised"])))

    def test_external_inputs_and_pass_snapshots(self):
        r = run((ROOT / "samples/demo_optimizations.tac").read_text())
        for key in ("folded", "simplified", "cse_blocks", "optimised"):
            self.assertEqual(execute(flatten(r[key]), {"a": 7, "b": 3}), 10)
        self.assertTrue(all(p.transformations > 0 for p in r["impact"].passes))

    def test_cse_overwritten_holder_and_self_update(self):
        for source in ["t = a + b\nt = 0\nu = a + b\nreturn u", 
                       "a = a + b\nu = a + b\nreturn u",
                       "t = a + b\na = a + b\nu = a + b\nreturn u",
                       "t = a + b\nu = a + b\nt = 0\nv = a + b\nreturn v"]:
            optimized, _ = cse_all(build_blocks(parse(source)))
            self.assertEqual(execute(flatten(optimized), {"a": 2, "b": 3}), execute(parse(source), {"a": 2, "b": 3}))

    def test_seeded_tac_equivalence(self):
        rng = random.Random(42)
        names = ["a", "b", "c", "t", "u"]
        for case in range(120):
            lines = []
            for _ in range(18):
                dest, left, right = rng.choice(names), rng.choice(names + ["0", "1", "2"]), rng.choice(names + ["0", "1", "2"])
                lines.append(f"{dest} = {left} {rng.choice(['+', '-', '*', '<', '=='])} {right}")
            source = "\n".join(lines + ["return u"])
            inputs = dict(zip(names, [1, 2, 3, 4, 5]))
            expected = execute(parse(source), inputs)
            result = run(source)
            for key in ("folded", "simplified", "cse_blocks", "optimised"):
                self.assertEqual(execute(flatten(result[key]), inputs), expected, f"case {case}, {key}")

    def test_empty_programs(self):
        for r in (run(""), run_source("// empty\n")):
            self.assertEqual(r["impact"].overall_reduction_pct, 0)
            self.assertEqual(r["final_cfg"].edges(), [])

    def test_documented_demo_results(self):
        for name, expected in (("sample_source.src", 1), ("demo_scope.src", 13),
                               ("demo_numbers.src", -1.5), ("demo_branches.src", 6)):
            self.check_source((ROOT / "samples" / name).read_text(encoding="utf-8"), expected)
        with self.assertRaises(CompilationError):
            run_source((ROOT / "samples/demo_errors.src").read_text(encoding="utf-8"))


class DiagnosticTests(unittest.TestCase):
    def test_lexer_position_and_partial_tokens(self):
        with self.assertRaises(LexError) as caught:
            run_source("int x = 1;\n  @")
        self.assertEqual((caught.exception.line, caught.exception.column), (2, 3))
        self.assertTrue(caught.exception.partial_result["tokens"])

    def test_comments_and_crlf_positions(self):
        tokens = tokenize("/* a\n b */\r\n  int x=1;")
        self.assertEqual((tokens[0].line, tokens[0].column), (3, 3))
        with self.assertRaises(LexError): tokenize("/* missing close")

    def test_unterminated_and_nonfinite_literals(self):
        for source in ("/* unclosed", "float x=1e9999;"):
            with self.assertRaises(LexError): run_source(source)

    def test_syntax_retains_tokens_and_stops(self):
        with patch("optimizer.codegen.generate") as generate:
            with self.assertRaises(ParseError) as caught: run_source("int x = ;")
            generate.assert_not_called()
        self.assertIn("tokens_text", caught.exception.partial_result)
        self.assertNotIn("ast_text", caught.exception.partial_result)

    def test_semantic_errors_collect_and_stop_codegen(self):
        with patch("optimizer.codegen.generate") as generate:
            with self.assertRaises(CompilationError) as caught: run_source("x=1; y=2;")
            generate.assert_not_called()
        self.assertIn("'x'", str(caught.exception))
        self.assertIn("'y'", str(caught.exception))
        self.assertIn("ast_text", caught.exception.partial_result)
        self.assertNotIn("tac_text", caught.exception.partial_result)

    def test_uninitialized_and_duplicate_declarations(self):
        for source in ("int x; return x;", "int x=1; int x=2;", "int x=x;"):
            with self.assertRaises(CompilationError): run_source(source)

    def test_branch_and_loop_definite_assignment(self):
        for source in ("int x; if(1) { x=1; } return x;",
                       "int x; while(0) { x=1; } return x;"):
            with self.assertRaises(CompilationError): run_source(source)
        result = run_source("int x; if(1) {x=2;} else {x=3;} return x;")
        self.assertEqual(execute(flatten(result["optimised"])), 2)

    def test_float_modulo_and_constant_zero(self):
        for source in ("return 3.2 % 2;", "return 4 / (2-2);"):
            with self.assertRaises(CompilationError): run_source(source)

    def test_propagated_zero_not_executed(self):
        r = run_source("int z=0; return 4/z;")
        self.assertIn("zero divisor", r["diagnostics_text"])
        self.assertIn("4 / 0", r["optimised_text"])

    def test_bad_tac(self):
        for source in ("L:\nL:", "goto missing", "1 = x", "x = ???", "x = 1e9999", "x = 3.2 % 2"):
            with self.assertRaises(CompilationError): run(source)

    def test_direct_tac_comments_and_truthy_branch(self):
        r = run("x = 1 # hello\nif x goto YES\nreturn 0\nYES:\nreturn 1")
        self.assertEqual(execute(flatten(r["optimised"])), 1)


class ImpactAndCLITests(unittest.TestCase):
    def test_impact_counts_and_arithmetic(self):
        r = run("a = 2 + 3\nreturn a")
        p = r["impact"].passes[0]
        self.assertEqual((p.before_count, p.after_count, p.transformations), (2, 2, 2))
        self.assertEqual((p.before_operations, p.after_operations), (1, 0))
        self.assertEqual(r["impact"].overall_reduction_pct, 0)
        r["impact_text"].encode("ascii")

    def test_removal_does_not_count_shifted_unchanged_instructions(self):
        r = run("if 0 > 1 goto L\nx = a + b\nL:\nreturn x")
        self.assertEqual(r["impact"].passes[-1].transformations, 1)

    def test_cli_success_error_and_file_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "test.src"
            for text, expected_code in (("return 2+3;", 0), ("int x=;", 1), ("missing=2;", 1)):
                source.write_text(text, encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", str(ROOT / "main.py"), str(source)], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected_code, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
            result = subprocess.run([sys.executable, "-B", str(ROOT / "main.py"), str(Path(folder)/"absent.src")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("File input", result.stderr)

    def test_cli_cp1252_output(self):
        import os
        environment = dict(os.environ, PYTHONIOENCODING="cp1252")
        result = subprocess.run([sys.executable, "-B", str(ROOT / "main.py"), str(ROOT / "samples/sample1.tac")], env=environment, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"IMPACT REPORT", result.stdout)


if __name__ == "__main__": unittest.main()
