class CFG:
    def __init__(self, blocks):
        self.blocks = blocks
        self.succ = {b.name: [] for b in blocks}
        self.pred = {b.name: [] for b in blocks}
        self._build()

    def _label_map(self):
        m = {}
        for b in self.blocks:
            first = b.instrs[0]
            if first.kind == "label":
                m[first.target] = b.name
        return m

    def _add(self, a, b):
        if b not in self.succ[a]:
            self.succ[a].append(b)
            self.pred[b].append(a)

    def _build(self):
        labels = self._label_map()
        for i, b in enumerate(self.blocks):
            last = b.instrs[-1]
            nxt = self.blocks[i + 1].name if i + 1 < len(self.blocks) else None
            if last.kind == "goto":
                self._add(b.name, self._resolve(labels, last.target))
            elif last.kind == "cond":
                self._add(b.name, self._resolve(labels, last.target))
                if nxt:
                    self._add(b.name, nxt)
            elif last.kind == "return":
                pass
            elif nxt:
                self._add(b.name, nxt)

    @staticmethod
    def _resolve(labels, target):
        if target not in labels:
            raise ValueError(f"Jump to undefined label '{target}'")
        return labels[target]

    def edges(self):
        return [(a, b) for a in self.succ for b in self.succ[a]]

    def unreachable(self):
        if not self.blocks:
            return []
        seen, stack = set(), [self.blocks[0].name]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.succ[n])
        return [b.name for b in self.blocks if b.name not in seen]
