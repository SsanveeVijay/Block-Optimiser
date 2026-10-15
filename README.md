# Basic-Block Optimizer 

**Problem:** Design and implement a basic-block optimizer. Construct basic blocks
and a control-flow graph, then apply constant folding, algebraic simplification,
and common subexpression elimination.

## Pipeline Stages

| Stage | Module | Description |
|---|---|---|
| **Lexical Analysis** | `optimizer/lexer.py` | Tokenises source code into a token stream |
| **Syntax Analysis** | `optimizer/parser_ast.py` | Recursive-descent parser; produces an AST |
| **Semantic Analysis** | `optimizer/semantic.py` | Scope/symbol table, type checking, undeclared-var detection |
| **Intermediate Code Gen** | `optimizer/codegen.py` | Walks AST → emits Three-Address Code (TAC) |
| **Basic Block Construction** | `optimizer/basic_blocks.py` | Leader algorithm → basic blocks |
| **Control Flow Graph** | `optimizer/cfg.py` | CFG + unreachable-block detection |
| **Constant Folding** | `optimizer/constant_folding.py` | Folds constants and propagates them locally |
| **Algebraic Simplification** | `optimizer/algebraic_simplification.py` | Identity/zero rules (x+0, x*1, x*0, x-x, …) |
| **CSE** | `optimizer/cse.py` | Local common subexpression elimination |

## Run (Python 3.8+, no external packages)

```bash
python gui.py                            # GUI with tabbed pipeline view
python main.py --src samples/sample_source.src   # Full pipeline (source → TAC → optimise)
python main.py samples/sample1.tac       # TAC-only (legacy mode)
python -m unittest discover tests        # All unit tests (33 tests)
```

## Input Formats

### Source language (`.src`) – full pipeline
```c
int a = 2 + 3;
int b = a * 4;
while (i < 10) { i = i + 1; }
if (x > 0) { return x; } else { return 0; }
```

### Three-Address Code (`.tac`) – optimisation only
```
x = a + b    # binop assign
x = a        # copy assign
L1:          # label
goto L1      # unconditional jump
if a < b goto L1   # conditional jump
return x
```

## GUI

The GUI (`gui.py`) shows **9 tabs** — one per pipeline stage — for any input.
Load a `.src` file for the full pipeline or a `.tac` file for the optimisation-only view.

## Future Scope
- Folding of constant conditional jumps + CFG pruning
- Global (inter-block) CSE and constant propagation
- Graph drawing of the CFG in the GUI
