import os
import tkinter as tk
from tkinter import ttk, messagebox

from optimizer.pipeline import run

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basic-Block Optimizer - Review 1")
        self.geometry("1000x620")

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        ttk.Label(left, text="Input (three-address code)").pack(anchor="w")
        self.inp = tk.Text(left, width=38, height=24, font=("Courier", 11))
        self.inp.pack()

        row = ttk.Frame(left)
        row.pack(fill="x", pady=6)
        self.sample = ttk.Combobox(
            row,
            values=sorted(os.listdir(SAMPLES)),
            state="readonly",
            width=16
        )
        self.sample.pack(side="left")
        ttk.Button(row, text="Load", command=self.load).pack(side="left", padx=4)
        ttk.Button(row, text="Analyze", command=self.analyze).pack(side="left")

        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.out = {}

        for key, title in [
            ("blocks_text", "Basic Blocks"),
            ("cfg_text", "CFG"),
            ("folded_text", "After Constant Folding"),
            ("log_text", "Change Log"),
        ]:
            t = tk.Text(self.tabs, font=("Courier", 11), state="disabled")
            self.tabs.add(t, text=title)
            self.out[key] = t

        self.sample.current(0)
        self.load()
        self.analyze()

    def load(self):
        path = os.path.join(SAMPLES, self.sample.get())
        with open(path) as f:
            self.inp.delete("1.0", "end")
            self.inp.insert("1.0", f.read())

    def analyze(self):
        try:
            res = run(self.inp.get("1.0", "end"))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        for key, widget in self.out.items():
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", res[key])
            widget.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
