"""
gui.py  –  Tkinter GUI for the Basic-Block Compiler & Optimizer.

Two modes:
  • TAC mode   : input is raw three-address code (.tac files)
  • Source mode: input is simple C-like source code (.src files)
                 Full pipeline: Lex → Parse → Semantic → Codegen → Optimise
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from optimizer.pipeline import run, run_source

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basic-Block Compiler & Optimizer — Review 2")
        self.geometry("1150x700")

        # ------------------------------------------------------------------ #
        #  Left panel                                                         #
        # ------------------------------------------------------------------ #
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)

        ttk.Label(left, text="Input").pack(anchor="w")
        self.inp = tk.Text(left, width=40, height=28, font=("Courier", 11))
        self.inp.pack()

        row = ttk.Frame(left)
        row.pack(fill="x", pady=6)

        sample_files = sorted(os.listdir(SAMPLES))
        self.sample = ttk.Combobox(row, values=sample_files,
                                   state="readonly", width=20)
        self.sample.pack(side="left")
        ttk.Button(row, text="Load", command=self.load).pack(side="left", padx=4)
        ttk.Button(row, text="Run Pipeline", command=self.analyze).pack(side="left")

        # Mode label
        self.mode_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.mode_var,
                  foreground="gray").pack(anchor="w", pady=(4, 0))

        # ------------------------------------------------------------------ #
        #  Right panel – tabs                                                 #
        # ------------------------------------------------------------------ #
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.out: dict[str, tk.Text] = {}

        # Tabs in pipeline order
        tab_defs = [
            ("ast_text",        "1. AST"),
            ("semantic_text",   "2. Semantic"),
            ("tac_text",        "3. TAC (Generated)"),
            ("blocks_text",     "4. Basic Blocks"),
            ("cfg_text",        "5. CFG"),
            ("folded_text",     "6. Constant Folding"),
            ("simplified_text", "7. Algebraic Simpl."),
            ("optimised_text",  "8. After CSE"),
            ("log_text",        "9. Change Log"),
        ]

        for key, title in tab_defs:
            frame = ttk.Frame(self.tabs)
            self.tabs.add(frame, text=title)
            t = tk.Text(frame, font=("Courier", 10), state="disabled",
                        wrap="none")
            vsb = ttk.Scrollbar(frame, orient="vertical", command=t.yview)
            hsb = ttk.Scrollbar(frame, orient="horizontal", command=t.xview)
            t.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            vsb.pack(side="right", fill="y")
            hsb.pack(side="bottom", fill="x")
            t.pack(fill="both", expand=True)
            self.out[key] = t

        # Load first sample
        if sample_files:
            self.sample.current(0)
            self.load()
            self.analyze()

    # ---------------------------------------------------------------------- #

    def load(self):
        name = self.sample.get()
        path = os.path.join(SAMPLES, name)
        with open(path) as f:
            self.inp.delete("1.0", "end")
            self.inp.insert("1.0", f.read())

    def _set_tab(self, key: str, text: str):
        w = self.out[key]
        w.config(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", text)
        w.config(state="disabled")

    def analyze(self):
        src = self.inp.get("1.0", "end").strip()
        name = self.sample.get()
        is_source = name.endswith(".src")

        try:
            if is_source:
                res = run_source(src)
                self.mode_var.set("Mode: Source (full pipeline)")
            else:
                res = run(src)
                self.mode_var.set("Mode: TAC (direct)")
        except Exception as e:
            messagebox.showerror("Pipeline Error", str(e))
            return

        # --- populate all tabs ---
        if is_source:
            self._set_tab("ast_text",        res.get("ast_text", ""))
            self._set_tab("semantic_text",    res.get("semantic_text", ""))
            self._set_tab("tac_text",         res.get("tac_text", ""))
        else:
            self._set_tab("ast_text",
                "N/A — load a .src file to see the AST.\n\n"
                "(TAC files skip directly to basic-block construction.)")
            self._set_tab("semantic_text",
                "N/A — load a .src file to see semantic analysis.")
            self._set_tab("tac_text",
                "N/A — TAC was provided directly as input.")

        self._set_tab("blocks_text",     res.get("blocks_text", ""))
        self._set_tab("cfg_text",        res.get("cfg_text", ""))
        self._set_tab("folded_text",     res.get("folded_text", ""))
        self._set_tab("simplified_text", res.get("simplified_text", ""))
        self._set_tab("optimised_text",  res.get("optimised_text", ""))
        self._set_tab("log_text",        res.get("log_text", ""))


if __name__ == "__main__":
    App().mainloop()
