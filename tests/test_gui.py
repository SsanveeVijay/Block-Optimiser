"""Hidden-window GUI checks; skip when Tk/display support is unavailable."""
import unittest

try:
    import tkinter as tk
    from gui import App, STAGES, TAB_GROUPS
except ImportError:
    tk = None


@unittest.skipIf(tk is None, "Tkinter is not installed")
class GUITests(unittest.TestCase):
    def setUp(self):
        try:
            self.app = App(visible=False)
        except tk.TclError as error:
            self.skipTest(f"No Tk display: {error}")

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.destroy()

    def analyze(self, text, mode="Source"):
        self.app.mode_var.set(mode)
        self.app.inp.delete("1.0", "end")
        self.app.inp.insert("1.0", text)
        self.app.analyze()
        self.app.update_idletasks()

    def test_all_stages_are_accessible(self):
        self.analyze("int x=2+3; return x;")
        for key, _ in STAGES:
            self.app.select_view(key)
            self.assertTrue(self.app.pages[key].winfo_exists())
            for notebook, frame in self.app.view_tabs[key]:
                self.assertEqual(notebook.select(), str(frame))
        self.assertIn("NUMBER", self.app.out["tokens_text"].get("1.0", "end"))

    def test_original_tab_structure_is_preserved(self):
        titles = [self.app.tabs.tab(tab, "text") for tab in self.app.tabs.tabs()]
        self.assertEqual(titles[:9], ["1. AST", "2. Semantic", "3. TAC", "4. Blocks",
                                     "5. CFG", "6. Folding", "7. Algebra", "8. CSE", "9. Log"])
        self.assertEqual(titles[9], "Impact")
        self.assertEqual(len(STAGES), sum(len(views) for _, views in TAB_GROUPS))
        self.assertEqual(self.app.inp.cget("width"), 40)

    def test_failure_preserves_input_and_clears_old_results(self):
        self.analyze("return 5;")
        self.analyze("int x; return x;")
        self.assertEqual(self.app.inp.get("1.0", "end-1c"), "int x; return x;")
        self.assertIn("Semantic analysis", self.app.out["diagnostics_text"].get("1.0", "end"))
        self.assertIn("Not reached", self.app.out["optimised_text"].get("1.0", "end"))
        self.assertNotIn("tac_text", self.app.last_result)
        for notebook, frame in self.app.view_tabs["diagnostics_text"]:
            self.assertEqual(notebook.select(), str(frame))
        self.assertFalse(self.app.graphs["final_graph"].canvas.find_withtag("edge"))

    def test_input_mode_is_independent_of_sample_selection(self):
        self.app.sample.set("sample1.tac")
        self.analyze("return 6;", mode="Source")
        self.assertEqual(self.app.last_result["mode"], "source")
        self.analyze("return 7", mode="TAC")
        self.assertEqual(self.app.last_result["mode"], "tac")
        self.assertIn("Not applicable", self.app.out["ast_text"].get("1.0", "end"))

    def test_graph_edges_and_unreachable_style(self):
        self.analyze("if a > 0 goto YES\nreturn 0\nYES:\nreturn 1\nUNUSED:\nreturn 2", "TAC")
        cfg = self.app.last_result["cfg"]
        view = self.app.graphs["original_graph"].canvas
        self.assertEqual(len(view.find_withtag("edge")), len(cfg.edges()))
        self.assertTrue(any(view.itemcget(item, "fill") == "#fff0ed"
                            for item in view.find_all() if view.type(item) == "rectangle"))
        self.assertFalse(self.app.last_result["final_cfg"].unreachable())

    def test_empty_and_long_instruction_graph(self):
        self.analyze("", "TAC")
        self.assertIn("Empty program", " ".join(self.app.graphs["final_graph"].canvas.itemcget(i, "text")
                        for i in self.app.graphs["final_graph"].canvas.find_all()))
        name = "long_variable_name_" * 12
        self.analyze(f"{name} = 2\nreturn {name}", "TAC")
        canvas = self.app.graphs["original_graph"].canvas
        rectangle = next(i for i in canvas.find_all() if canvas.type(i) == "rectangle")
        self.assertGreater(canvas.coords(rectangle)[3] - canvas.coords(rectangle)[1], 100)


if __name__ == "__main__":
    unittest.main()
