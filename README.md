# Basic-Block Compiler and Optimizer

A Python teaching compiler for a small C-like language and direct three-address
code (TAC). Both entry points construct basic blocks and a control-flow graph,
then run constant folding/propagation, algebraic simplification, local CSE,
and constant-branch/unreachable-block cleanup. GUI and CLI use the same pipeline.

Work continues on branch `finish-project`, based on `92cb1ec`. Existing history
is preserved. Implementation changes and checks are documented here.

## Run

Python 3.10+; no third-party packages. The desktop GUI requires Tkinter.

```text
python -B gui.py
python -B main.py samples/sample_source.src
python -B main.py --src samples/sample_source.src
python -B main.py samples/sample1.tac
python -B -m unittest discover -s tests -v
```

The CLI detects `.src` files; use `--src` or `--tac` to override. Input files use
UTF-8 (an optional BOM is accepted). Expected input failures report the compiler
stage and available source position, exit with status 1, and do not print a
Python traceback. Bad command-line arguments exit with status 2.

## Implemented pipeline

| Stage | Module | Behavior |
| --- | --- | --- |
| Lexical analysis | `optimizer/lexer.py` | Tokens with line/column positions; line and block comments |
| Syntax analysis | `optimizer/parser_ast.py` | Recursive-descent AST; arithmetic, comparison and equality precedence |
| Semantic analysis | `optimizer/semantic.py` | Scoped declarations, duplicate/undeclared names, definite assignment, numeric diagnostics |
| Intermediate code | `optimizer/codegen.py` | TAC, unique scoped names/temporaries, explicit int/float conversions |
| Blocks and CFG | `optimizer/basic_blocks.py`, `optimizer/cfg.py` | Leaders, predecessors/successors and reachability |
| Constant folding | `optimizer/constant_folding.py` | Local constant propagation and safe numeric folding |
| Algebraic simplification | `optimizer/algebraic_simplification.py` | Integer identities including x+0, x*1, x*0, x-x and x/1 |
| Local CSE | `optimizer/cse.py` | Reuse identical expressions; invalidate changed operands AND overwritten result holders |
| Control-flow cleanup | `optimizer/control_flow.py` | Replace known-true branches, remove known-false branches, rebuild CFG, remove unreachable blocks |
| Impact report | `optimizer/impact_analyzer.py` | Per-pass instruction changes, arithmetic counts, reductions and ASCII bar chart |
| CFG drawing | `optimizer/cfg_view.py` | Scrollable before/after graphs, branch labels, loop edges and unreachable-block highlighting |

Original blocks/CFG and every pass snapshot remain available alongside final
optimized TAC/CFG. Instruction counts exclude labels. A rewrite can reduce the
number of binary operations while leaving the number of instructions unchanged.
The report does not claim measured execution-time speedups.

## Source language

```c
int a = 2 + 3;
int b = a * 4;
int i = 0;
while (i < 3) {
    i = i + 1;
}
if (b > 10) { b = b + i; } else { b = 0; }
return b;
```

Supported: `int`, `float`, declarations, assignment, braces, `if`/`else`, `while`,
`return`, parentheses, unary minus, `+ - * / %`, `< > <= >= == !=`, `//` and
`/* ... */` comments. Keywords are case-sensitive; identifiers use ASCII letters,
digits and underscores and cannot start with a digit. Decimal/exponent literals
are supported. A semicolon ends declarations, assignments and return statements.
Conditions and loop bodies require braces. Nonzero numeric conditions are true.
No functions, arrays, strings, logical operators, for loops or machine-code backend.

### Numeric and scope rules

- Integers are unbounded; integer division truncates toward zero, and remainder
  has the dividend's sign. Float arithmetic uses Python double precision.
- Mixed arithmetic promotes to float. Comparisons produce integer 0 or 1.
- Assignment to `int` truncates a float toward zero; assignment to `float`
  converts integers to float. Type conversions/mixed arithmetic produce warnings.
  TAC makes necessary assignment conversions explicit.
- Modulo requires integers. Non-finite numeric literals are rejected.
- Integer algebraic identities are skipped for any program containing float
  declarations/literals/casts, avoiding unsafe floating-point identities.
- Nested declarations may shadow outer names. Generated names such as `__v0_x`
  preserve separate storage; temporaries use `__t0`, labels `__L0`.
- Variables must be declared and definitely initialized before use. Initialization
  after an if requires both branches; a loop alone does not establish initialization
  after the loop (it might execute zero times). This check is conservative.

### Error handling

Lexical/syntax/TAC errors stop at the first failure. Semantic analysis collects
multiple issues and stops code generation if any are errors; warnings allow it.
Completed tokens/AST/semantic output can still be inspected after a later failure.
Duplicate TAC labels, malformed operands, and undefined targets are rejected.
A literal-only zero divisor in source is a semantic error. A zero divisor exposed
later by propagation is retained and reported as a warning; optimization never
executes it. Runtime-dependent division by zero/overflow is outside this static tool.

## Direct TAC

One instruction per line; spaces separate tokens. Blank lines and `#` comments
(including inline comments) are allowed. Variables can represent external inputs;
source-language declaration/initialization checks do not apply to direct TAC.

```text
x = a + b
copy = x
n = int value
f = float n
L1:
if x > 0 goto L2
if x goto L2
goto L1
L2:
return x
```

Labels must be unique and targets must exist. Integers/finite decimals are accepted.
Conversions use `dest = int operand` or `dest = float operand`. Direct TAC does
not carry a type table: casts and numeric literals determine numeric operations.
External values in an integer-only TAC program are assumed to be integers. Include
explicit float conversions when working with floating-point external values.

## Desktop interface

The original structure is retained: input editor on the left, sample selector,
**Load** and **Run Pipeline** beneath it, and output tabs on the right. The window
starts at the original 1150x700 size. The left panel also includes a **Source/TAC**
mode selector and **Open file**. Mode is independent of the selected sample;
loading a sample or opening a file sets it from the extension. The initial source
sample is analyzed automatically; click **Run Pipeline** after loading or editing.

The original nine pipeline tabs remain in order: AST, Semantic, TAC, Blocks,
CFG, Folding, Algebra, CSE and Log. An **Impact** tab is appended. Related new
output uses subtabs: Tokens under AST; Symbols and Diagnostics under Semantic;
original/final text and drawings under CFG; final optimized TAC under CSE. All
17 output views remain available through tabs, without a stage dropdown.
Graphs scroll in both directions and highlight originally unreachable blocks.
The final graph reflects branch simplification and unreachable-block removal.

On failure, the editor retains the program and Diagnostics identifies the stage
that stopped. Completed-stage output remains available; later views are cleared
and marked as not reached. Direct TAC marks frontend views as not applicable.

## Demo samples

| File in `samples/` | Demonstrates | Expected behavior |
| --- | --- | --- |
| `sample_source.src` | Full pipeline with a loop and if/else | Return value 1 |
| `sample1.tac`, `sample2.tac` | Original direct TAC examples | Blocks, CFG and optimization results |
| `demo_optimizations.tac` | All three passes plus branch cleanup | With external a=7, b=3, return value 10 |
| `demo_scope.src` | Shadowing and generated-name safety | Return value 13 |
| `demo_numbers.src` | Float arithmetic and numeric conversions | Return value -1.5; conversion warnings |
| `demo_branches.src` | Constant condition and unreachable else | Return value 6; pruned final CFG |
| `demo_errors.src` | Uninitialized and undeclared variables | Semantic errors; no generated TAC |

Return values describe program semantics verified in tests. The application
displays generated/optimized TAC; it does not execute the program.

## Completion work

Implemented correctness repairs: CSE result-holder invalidation, shadowing,
temporary collisions, arithmetic conditions, equality precedence, recursive unary
minus, and explicit numeric conversions. Added structured stage failures and
retention of completed results, plus control-flow cleanup and the impact report.

The interface preserves the original tabbed layout, with explicit input mode,
file opening, original/final CFG drawings, diagnostics and the impact report. Added focused
demo samples for optimization, control flow, numbers, scopes and invalid input.

## Verification

Run `python -B -m unittest discover -s tests -v`. The suite contains the original
33 checks plus regression checks for the completion work. A bounded independent
TAC executor lives only in `tests/tac_runner.py`; it compares results before and
after every pass, including 120 deterministic generated integer programs. It is
test infrastructure, not an application runtime.

GUI tests use hidden Tk windows to verify the original tab order, access to every
output view, independent input mode, graph edges/long instruction wrapping, and
clearing stale output on errors.
They skip on systems without Tkinter or a display. CLI tests cover success,
compiler failures, missing files and Windows CP1252 output. The CLI tests need
permission to create ordinary temporary files.

All demo return values in the table above are checked against both generated
and optimized TAC. Verification on Windows/Python 3.13, October 22, 2026:
the **66 compiler/CLI tests passed**, and **all 6 GUI tests passed (no skips)**
after restoring the original layout. The current suite contains 72 tests.
The generated-program test compares every optimization snapshot for 120 seeded
integer programs. All seven valid sample files compile successfully; the invalid
sample stops at semantic analysis as intended. `git diff --check` is clean.

## Boundaries

Constant propagation and CSE are local to each basic block. There is no global
data-flow optimization, general dead-assignment elimination, program execution
feature, or native machine-code generation. Unreachable-block removal follows
constant-branch simplification. Reports and presentations are maintained separately;
the outcome/manuscript/patent and contribution presentation are outside this code work.
