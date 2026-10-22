"""Static instruction and arithmetic counts, not runtime measurements."""
from dataclasses import dataclass
from difflib import SequenceMatcher

@dataclass
class PassReport:
    name: str
    before_count: int
    after_count: int
    transformations: int
    reduction_pct: float
    before_operations: int
    after_operations: int

@dataclass
class ImpactReport:
    passes: list
    original_count: int
    final_count: int
    total_transformations: int
    overall_reduction_pct: float

    def summary_text(self):
        lines = ["OPTIMIZATION IMPACT REPORT (static counts)",
                 f"Original instructions: {self.original_count}",
                 f"Final instructions: {self.final_count}",
                 f"Total transformations across passes: {self.total_transformations}",
                 f"Overall instruction reduction: {self.overall_reduction_pct:.1f}%", ""]
        for item in self.passes:
            lines.extend([item.name,
                f"  Instructions: {item.before_count} -> {item.after_count}",
                f"  Changed/removed/added: {item.transformations}",
                f"  Binary operations: {item.before_operations} -> {item.after_operations}",
                f"  Instruction reduction: {item.reduction_pct:.1f}%"])
        lines.extend(["", "Instruction counts:"])
        counts = [("Original", self.original_count)] + [(p.name, p.after_count) for p in self.passes]
        maximum = max([n for _, n in counts] + [1])
        for label, count in counts:
            lines.append(f"{label:<32} |{'#' * round(32 * count / maximum)} {count}")
        lines.extend(["", "Labels are excluded. Rewrites can reduce arithmetic without reducing instruction count.",
                      "Counts do not measure execution time or prove a runtime speedup."])
        return "\n".join(lines)


def analyze(original_blocks, pass_results):
    def instructions(blocks):
        return [i for b in blocks for i in b.instrs if i.kind != "label"]
    previous = instructions(original_blocks)
    original_count = len(previous)
    reports = []
    for name, blocks in pass_results:
        current = instructions(blocks)
        matcher = SequenceMatcher(a=[str(i) for i in previous], b=[str(i) for i in current], autojunk=False)
        changes = sum(max(b-a, d-c) for tag, a, b, c, d in matcher.get_opcodes() if tag != "equal")
        reduction = (len(previous) - len(current)) / len(previous) * 100 if previous else 0.0
        reports.append(PassReport(name, len(previous), len(current), changes, reduction,
                                  sum(i.kind == "binop" for i in previous),
                                  sum(i.kind == "binop" for i in current)))
        previous = current
    reduction = (original_count - len(previous)) / original_count * 100 if original_count else 0.0
    return ImpactReport(reports, original_count, len(previous), sum(p.transformations for p in reports), reduction)
