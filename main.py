import sys
from optimizer.pipeline import run

if len(sys.argv) != 2:
    sys.exit("usage: python main.py <file.tac>")
with open(sys.argv[1]) as f:
    res = run(f.read())
print("=== BASIC BLOCKS ===\n" + res["blocks_text"])
print("=== CFG ===\n" + res["cfg_text"])
print("\n=== AFTER CONSTANT FOLDING ===\n" + res["folded_text"])
print("=== CHANGES ===\n" + res["log_text"])
