"""Scrollable Tk canvas rendering of a CFG, without external graph packages."""
import tkinter as tk
from tkinter import ttk


class CFGView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background="#f7f9fc", highlightthickness=0)
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

    def draw(self, cfg=None, message="Run the pipeline to see the graph."):
        c = self.canvas
        c.delete("all")
        if cfg is None or not cfg.blocks:
            c.create_text(24, 24, anchor="nw", text=message if cfg is None else "Empty program: no blocks.")
            c.configure(scrollregion=(0, 0, 600, 300))
            return
        unreachable = set(cfg.unreachable())
        positions = {}
        y = 55
        width = 420
        # A vertical layout keeps source order readable; side lanes show branches/back edges.
        lanes = max(len(cfg.edges()), 1)
        x = 80 + lanes * 14
        for block in cfg.blocks:
            lines = [str(i) for i in block.instrs]
            text = c.create_text(x + 12, y + 38, anchor="nw", width=width - 24,
                                 text="\n".join(lines), font=("Consolas", 10), tags="node")
            height = max(62, c.bbox(text)[3] - y + 12)
            positions[block.name] = (x, y, x + width, y + height)
            fill = "#fff0ed" if block.name in unreachable else "#ffffff"
            rectangle = c.create_rectangle(x, y, x + width, y + height, fill=fill,
                                           outline="#74849a", width=2, tags="node")
            c.tag_lower(rectangle, text)
            status = " (unreachable)" if block.name in unreachable else ""
            c.create_text(x + 12, y + 12, anchor="nw", text=block.name + status,
                          font=("Segoe UI", 11, "bold"), fill="#1c2b43", tags="node")
            y += height + 76
        for index, (source, target) in enumerate(cfg.edges()):
            sx, sy, sr, sb = positions[source]
            tx, ty, tr, tb = positions[target]
            lane = 40 + index * 14
            middle_source, middle_target = (sy + sb) / 2, (ty + tb) / 2
            c.create_line(sx, middle_source, lane, middle_source, lane, middle_target,
                          tx, middle_target, arrow="last", width=2, fill="#526581", tags="edge")
            last = next(b for b in cfg.blocks if b.name == source).instrs[-1]
            label = ""
            if last.kind == "cond":
                target_labels = [i.target for b in cfg.blocks if b.name == target
                                 for i in b.instrs if i.kind == "label"]
                is_jump = last.target in target_labels
                next_index = next(i for i, b in enumerate(cfg.blocks) if b.name == source) + 1
                is_fallthrough = next_index < len(cfg.blocks) and cfg.blocks[next_index].name == target
                label = "true / false" if is_jump and is_fallthrough else ("true" if is_jump else "false")
            elif last.kind == "goto": label = "jump"
            else: label = "next"
            c.create_text(lane + 4, middle_source - 10, anchor="w", text=label,
                          fill="#354662", font=("Segoe UI", 9))
        c.tag_lower("edge")
        first = positions[cfg.blocks[0].name]
        c.create_text(first[0] + width / 2, 20, text="ENTRY", font=("Segoe UI", 10, "bold"))
        for block in cfg.blocks:
            if not cfg.succ[block.name]:
                left, top, right, bottom = positions[block.name]
                c.create_text(right + 35, (top + bottom) / 2, text="EXIT", anchor="w")
        c.configure(scrollregion=(0, 0, x + width + 110, y))
