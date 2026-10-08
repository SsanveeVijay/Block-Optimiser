# Basic-Block Optimizer (Project Review 1 - ~25%)

**Problem:** Design and implement a basic-block optimizer. Construct basic blocks
and a control-flow graph, then apply constant folding, algebraic simplification,
and common subexpression elimination.

## Done so far (~25%)
- Three-address-code parser (`optimizer/tac.py`)
- Basic block construction via the leader algorithm (`optimizer/basic_blocks.py`)
- Control-flow graph + unreachable-block detection (`optimizer/cfg.py`)
- Constant folding with local constant propagation (`optimizer/constant_folding.py`)
- Very basic Tkinter GUI (`gui.py`), CLI (`main.py`), unit tests (`tests/`)

## Remaining
- Algebraic simplification (`optimizer/algebraic_simplification.py`, stub)
- Common subexpression elimination (`optimizer/cse.py`, stub)
- Folding of constant conditional jumps + CFG update, graph drawing in GUI

## Run (Python 3.8+, no external packages)
    python gui.py                       # GUI (needs tkinter)
    python main.py samples/sample1.tac  # command line
    python -m unittest discover tests   # tests

## Input format
One instruction per line, tokens separated by spaces:
`x = a + b`, `x = a`, `L1:`, `goto L1`, `if a < b goto L1`, `return x`
