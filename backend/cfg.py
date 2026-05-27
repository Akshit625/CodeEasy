from collections import defaultdict

class BasicBlock:
    def __init__(self, label=None):
        self.label = label
        self.instructions = []
        self.successors = []

def build_cfg(tac):
    if not tac:
        return []

    blocks = []
    leaders = set()
    leaders.add(0)  # First instruction
    labels = {}
    
    # Find leaders
    for i, instr in enumerate(tac):
        if instr[0] == 'label':
            leaders.add(i)
            labels[instr[1]] = i
        elif instr[0] in ['jump', 'if_false', 'return']:
            leaders.add(i + 1)
    
    # Build blocks
    current_block = None
    for i, instr in enumerate(tac):
        if i in leaders:
            if current_block:
                blocks.append(current_block)
            current_block = BasicBlock()
            if instr[0] == 'label':
                current_block.label = instr[1]
        current_block.instructions.append(instr)
    
    if current_block:
        blocks.append(current_block)
    
    # Build successors
    for block in blocks:
        last_instr = block.instructions[-1]
        if last_instr[0] == 'jump':
            target = labels[last_instr[1]]
            # Find block starting at target
            for b in blocks:
                if b.label and labels.get(b.label) == target:
                    block.successors.append(b)
                    break
        elif last_instr[0] == 'if_false':
            # Fall through and jump
            target = labels[last_instr[2]]
            for b in blocks:
                if b.label and labels.get(b.label) == target:
                    block.successors.append(b)
                    break
            # Next block
            idx = blocks.index(block) + 1
            if idx < len(blocks):
                block.successors.append(blocks[idx])
        elif last_instr[0] != 'return':
            # Fall through
            idx = blocks.index(block) + 1
            if idx < len(blocks):
                block.successors.append(blocks[idx])
    
    return blocks
