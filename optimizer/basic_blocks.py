from dataclasses import dataclass, field

@dataclass
class Block:
    name: str
    instrs: list = field(default_factory=list)


def find_leaders(prog) -> list:
    if not prog:
        return []
    leaders = {0}
    for i, ins in enumerate(prog):
        if ins.kind == "label":
            leaders.add(i)
        if ins.kind in ("goto", "cond", "return") and i + 1 < len(prog):
            leaders.add(i + 1)
    return sorted(leaders)


def build_blocks(prog) -> list:
    leaders = find_leaders(prog)
    blocks = []
    for k, start in enumerate(leaders):
        end = leaders[k + 1] if k + 1 < len(leaders) else len(prog)
        blocks.append(Block(f"B{k + 1}", prog[start:end]))
    return blocks
