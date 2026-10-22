"""Desktop compiler retaining the original input-left, output-tabs-right layout."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from optimizer.pipeline import run, run_source
from optimizer.diagnostics import CompilationError
from optimizer.cfg_view import CFGView

SAMPLES = Path(__file__).resolve().parent / "samples"
STAGES = [
    ("diagnostics_text", "Diagnostics"), ("tokens_text", "Tokens"),
    ("ast_text", "Syntax tree (AST)"), ("semantic_text", "Semantic analysis"),
    ("symbols_text", "Symbol names"), ("tac_text", "Generated TAC"),
    ("blocks_text", "Original basic blocks"), ("cfg_text", "Original CFG (text)"),
    ("original_graph", "Original CFG (drawing)"),
    ("folded_text", "Constant folding"), ("simplified_text", "Algebraic simplification"),
    ("cse_text", "Common subexpression elimination"), ("optimised_text", "Final optimized TAC"),
    ("final_cfg_text", "Final CFG (text)"), ("final_graph", "Final CFG (drawing)"),
    ("log_text", "Change log"), ("impact_text", "Optimization impact"),
]

# Keep the original nine pipeline tabs, grouping related new output beneath them.
TAB_GROUPS = [
    ("1. AST", [("ast_text", "AST"), ("tokens_text", "Tokens")]),
    ("2. Semantic", [("semantic_text", "Analysis"), ("symbols_text", "Symbols"),
                     ("diagnostics_text", "Diagnostics")]),
    ("3. TAC", [("tac_text", "Generated TAC")]),
    ("4. Blocks", [("blocks_text", "Basic Blocks")]),
    ("5. CFG", [("cfg_text", "Original text"), ("original_graph", "Original graph"),
                ("final_cfg_text", "Final text"), ("final_graph", "Final graph")]),
    ("6. Folding", [("folded_text", "Constant Folding")]),
    ("7. Algebra", [("simplified_text", "Algebraic Simplification")]),
    ("8. CSE", [("cse_text", "After CSE"), ("optimised_text", "Final optimized TAC")]),
    ("9. Log", [("log_text", "Change Log")]),
    ("Impact", [("impact_text", "Optimization Impact")]),
]


class App(tk.Tk):
    def __init__(self, visible=True):
        super().__init__()
        if not visible: self.withdraw()
        self.title("Basic-Block Compiler and Optimizer")
        self.geometry("1150x700")
        self.minsize(1100, 560)
        self.last_result = {}
        self.mode_var = tk.StringVar(value="Source")
        self.status = tk.StringVar(value="Ready")
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Label(left, text="Input").pack(anchor="w")
        self.inp = self._text(left, editable=True)
        row = ttk.Frame(left)
        row.pack(fill="x", pady=6)
        samples = sorted(p.name for p in SAMPLES.glob("*") if p.suffix in (".src", ".tac"))
        self.sample = ttk.Combobox(row, values=samples, state="readonly", width=20)
        self.sample.pack(side="left")
        ttk.Button(row, text="Load", command=self.load).pack(side="left", padx=4)
        ttk.Button(row, text="Run Pipeline", command=self.analyze).pack(side="left")
        mode_row = ttk.Frame(left)
        mode_row.pack(fill="x", pady=(4, 0))
        ttk.Label(mode_row, text="Mode:").pack(side="left")
        self.mode = ttk.Combobox(mode_row, textvariable=self.mode_var,
                                 values=["Source", "TAC"], state="readonly", width=9)
        self.mode.pack(side="left", padx=4)
        ttk.Button(mode_row, text="Open file", command=self.open_file).pack(side="left", padx=8)
        ttk.Label(left, textvariable=self.status, wraplength=355,
                  foreground="gray").pack(anchor="w", pady=(8, 0))

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.pages = {}
        self.out = {}
        self.graphs = {}
        self.view_tabs = {}
        for title, views in TAB_GROUPS:
            group = ttk.Frame(self.tabs)
            self.tabs.add(group, text=title)
            nested = None
            if len(views) > 1:
                nested = ttk.Notebook(group)
                nested.pack(fill="both", expand=True)
            for key, subtitle in views:
                frame = ttk.Frame(nested) if nested is not None else group
                parents = [(self.tabs, group)]
                if nested is not None:
                    nested.add(frame, text=subtitle)
                    parents.append((nested, frame))
                self.pages[key] = frame
                self.view_tabs[key] = parents
                if key.endswith("graph"):
                    view = CFGView(frame)
                    view.pack(fill="both", expand=True)
                    self.graphs[key] = view
                    view.draw()
                else:
                    self.out[key] = self._text(frame)
        self.select_view("ast_text")
        if samples:
            self.sample.set("sample_source.src" if "sample_source.src" in samples else samples[0])
            self.load()
            self.analyze()

    @staticmethod
    def _text(parent, editable=False):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, font=("Courier", 11 if editable else 10), wrap="none", undo=editable,
                       state="normal" if editable else "disabled", width=40, height=28)
        vertical = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        text.pack(fill="both", expand=True)
        return text

    def select_view(self, key):
        for notebook, frame in self.view_tabs[key]:
            notebook.select(frame)

    def _set_tab(self, key, value):
        widget = self.out[key]
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def show_result(self, result, failed=False):
        self.last_result = result
        is_source = self.mode_var.get() == "Source"
        source_keys = {"tokens_text", "ast_text", "semantic_text", "symbols_text", "tac_text"}
        for key in self.out:
            fallback = "Not reached in this run." if failed else "(no output)"
            if not is_source and key in source_keys:
                fallback = "Not applicable: direct TAC input skips the source-language frontend."
            self._set_tab(key, result.get(key, fallback))
        self.graphs["original_graph"].draw(result.get("cfg"), "Original CFG was not reached in this run.")
        self.graphs["final_graph"].draw(result.get("final_cfg"), "Final CFG was not reached in this run.")
        self.select_view("diagnostics_text" if failed else "ast_text" if is_source else "blocks_text")

    def read_file(self, path):
        try:
            content = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            messagebox.showerror("File input", str(error), parent=self)
            return
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", content)
        self.mode_var.set("Source" if Path(path).suffix.lower() == ".src" else "TAC")
        self.show_result({"diagnostics_text": "Input loaded. Run the pipeline to analyze it."}, failed=True)
        self.status.set(f"Loaded {Path(path).name} - {self.mode_var.get()} mode")

    def load(self):
        if self.sample.get(): self.read_file(SAMPLES / self.sample.get())

    def open_file(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Compiler input", "*.src *.tac"), ("All files", "*.*")])
        if path: self.read_file(path)

    def analyze(self):
        source = self.inp.get("1.0", "end-1c")
        try:
            result = (run_source if self.mode_var.get() == "Source" else run)(source)
        except CompilationError as error:
            result = {**error.partial_result, "diagnostics_text": str(error)}
            self.show_result(result, failed=True)
            self.status.set(f"Stopped at {error.stage}; see Diagnostics. Input is preserved.")
            return
        except RecursionError:
            self.show_result({"diagnostics_text": "[Input] Nesting is too deep; simplify the program."}, failed=True)
            self.status.set("Stopped: input nesting limit.")
            return
        self.show_result(result)
        self.status.set("Pipeline complete. Select an output tab to inspect the results.")


if __name__ == "__main__":
    App().mainloop()
