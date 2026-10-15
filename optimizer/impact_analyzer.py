"""
optimizer/impact_analyzer.py  –  Optimization Impact Analyzer (Novelty Feature)

Compares the original TAC against the optimized TAC and produces a structured
report covering:
  - Total instruction count before / after each pass
  - Number of transformations per pass
  - Percentage reduction in instruction count per pass
  - Overall reduction across the full pipeline
"""

from typing import List, Dict
from dataclasses import dataclass
from .tac import Instr


# --------------------------------------------------------------------------- #
#  Data structures                                                             #
# --------------------------------------------------------------------------- #

@dataclass
class PassReport:
    name: str
    before_count: int       # number of non-label, non-trivial instructions
    after_count: int
    transformations: int    # instructions that actually changed
    reduction_pct: float    # (before - after) / before * 100

    def __str__(self) -> str:
        arrow = "▼" if self.after_count < self.before_count else ("▲" if self.after_count > self.before_count else "–")
        return (
            f"  Pass : {self.name}\n"
            f"  Before : {self.before_count} instructions\n"
            f"  After  : {self.after_count} instructions  {arrow}\n"
            f"  Changed: {self.transformations} instruction(s)\n"
            f"  Reduction: {self.reduction_pct:.1f}%"
        )


@dataclass
class ImpactReport:
    passes: List[PassReport]
    original_count: int
    final_count: int
    total_transformations: int
    overall_reduction_pct: float

    def summary_text(self) -> str:
        lines = []
        lines.append("=" * 56)
        lines.append("  OPTIMIZATION IMPACT REPORT")
        lines.append("=" * 56)
        lines.append(f"  Original instruction count : {self.original_count}")
        lines.append(f"  Final instruction count    : {self.final_count}")
        lines.append(f"  Total transformations      : {self.total_transformations}")
        lines.append(
            f"  Overall reduction          : {self.overall_reduction_pct:.1f}%"
        )
        lines.append("")
        lines.append("── Per-Pass Breakdown ──────────────────────────────────")
        for i, pr in enumerate(self.passes, 1):
            lines.append(f"\n[Pass {i}] {pr.name}")
            lines.append(f"  Instructions before : {pr.before_count}")
            lines.append(f"  Instructions after  : {pr.after_count}")
            lines.append(f"  Transformations     : {pr.transformations}")
            lines.append(f"  Reduction           : {pr.reduction_pct:.1f}%")
        lines.append("")
        lines.append("── Bar Chart (instruction count per pass) ──────────────")
        all_counts = [self.original_count] + [p.after_count for p in self.passes]
        labels = ["Original"] + [p.name for p in self.passes]
        max_count = max(all_counts) if all_counts else 1
        bar_width = 40
        for label, count in zip(labels, all_counts):
            filled = int(bar_width * count / max_count) if max_count else 0
            bar = "█" * filled + "░" * (bar_width - filled)
            lines.append(f"  {label:<22} |{bar}| {count}")
        lines.append("=" * 56)
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Counting helpers                                                            #
# --------------------------------------------------------------------------- #

def _count_instructions(blocks) -> int:
    """Count total non-label instructions across all blocks."""
    total = 0
    for b in blocks:
        for ins in b.instrs:
            if ins.kind != "label":
                total += 1
    return total


def _count_transformations(original_blocks, new_blocks) -> int:
    """Count instructions that changed between two block lists."""
    orig_strs = [str(i) for b in original_blocks for i in b.instrs]
    new_strs  = [str(i) for b in new_blocks  for i in b.instrs]
    changed = 0
    for o, n in zip(orig_strs, new_strs):
        if o != n:
            changed += 1
    # Also count any net additions/removals
    changed += abs(len(new_strs) - len(orig_strs))
    return changed


# --------------------------------------------------------------------------- #
#  Public API                                                                  #
# --------------------------------------------------------------------------- #

def analyze(
    original_blocks,
    pass_results: List[tuple],   # list of (pass_name, optimized_blocks)
) -> ImpactReport:
    """
    Build an ImpactReport.

    Parameters
    ----------
    original_blocks : list[Block]
        Basic blocks before any optimisation.
    pass_results : list of (name, blocks)
        Each entry is the blocks produced after one optimisation pass,
        in pipeline order.
    """
    pass_reports: List[PassReport] = []
    prev_blocks = original_blocks
    prev_count  = _count_instructions(original_blocks)

    for name, blocks in pass_results:
        after_count = _count_instructions(blocks)
        transformations = _count_transformations(prev_blocks, blocks)
        reduction = (
            (prev_count - after_count) / prev_count * 100
            if prev_count > 0 else 0.0
        )
        pass_reports.append(PassReport(
            name=name,
            before_count=prev_count,
            after_count=after_count,
            transformations=transformations,
            reduction_pct=reduction,
        ))
        prev_blocks = blocks
        prev_count  = after_count

    original_count = _count_instructions(original_blocks)
    final_count    = prev_count
    total_transforms = sum(p.transformations for p in pass_reports)
    overall_pct = (
        (original_count - final_count) / original_count * 100
        if original_count > 0 else 0.0
    )

    return ImpactReport(
        passes=pass_reports,
        original_count=original_count,
        final_count=final_count,
        total_transformations=total_transforms,
        overall_reduction_pct=overall_pct,
    )
