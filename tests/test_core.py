import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from optimizer.pipeline import run
from optimizer.tac import parse, ParseError


class Tests(unittest.TestCase):
    def test_blocks_and_cfg(self):
        src = "x = 1\nif x > 0 goto L1\ny = 2\nL1:\nreturn x\n"
        r = run(src)
        self.assertEqual(len(r["blocks"]), 3)
        self.assertEqual(sorted(r["cfg"].edges()),
                         [("B1", "B2"), ("B1", "B3"), ("B2", "B3")])

    def test_loop_edges(self):
        r = run(open(os.path.join(ROOT, "samples", "sample1.tac")).read())
        self.assertIn(("B3", "B2"), r["cfg"].edges())

    def test_folding(self):
        r = run("a = 2 + 3\nb = a * 4\nreturn b\n")
        self.assertIn("b = 20", r["folded_text"])
        self.assertIn("return 20", r["folded_text"])

    def test_c_division(self):
        r = run("a = 0 - 7\nb = a / 2\nc = a % 2\nreturn b\n")
        self.assertIn("b = -3", r["folded_text"])
        self.assertIn("c = -1", r["folded_text"])

    def test_div_zero_not_folded(self):
        r = run("a = 4 / 0\nreturn a\n")
        self.assertIn("a = 4 / 0", r["folded_text"])

    def test_no_prop_across_redefinition(self):
        r = run("a = 1\na = b + 1\nc = a + 1\nreturn c\n")
        self.assertIn("c = a + 1", r["folded_text"])

    def test_bad_input(self):
        with self.assertRaises(ParseError):
            parse("this is nonsense")


if __name__ == "__main__":
    unittest.main()
