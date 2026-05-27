import re


IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def analyze_code(tac, cfg):
    analysis = {}

    # Unused variables
    analysis['unused_vars'] = find_unused_variables(tac)

    # Unreachable code
    analysis['unreachable'] = find_unreachable_code(cfg)

    # Live variables (simplified)
    analysis['live_vars'] = compute_live_variables(tac)

    # Redundant assignments
    analysis['redundant_assigns'] = find_redundant_assignments(tac)

    # Constant conditions
    analysis['constant_conds'] = find_constant_conditions(tac)

    return analysis


def is_identifier(value):
    return isinstance(value, str) and IDENTIFIER_PATTERN.fullmatch(value) is not None


def mark_used(used, value):
    if is_identifier(value):
        used.add(value)


def find_unused_variables(tac):
    defined = set()
    used = set()

    for instr in tac:
        if instr[0] == 'assign':
            defined.add(instr[1])
            mark_used(used, instr[2])
            if len(instr) > 4:
                mark_used(used, instr[4])
        elif instr[0] in ['if_false', 'return']:
            mark_used(used, instr[1])
        elif instr[0] == 'call':
            for arg in instr[2]:
                mark_used(used, arg)

    return defined - used


def find_unreachable_code(cfg):
    reachable = set()
    to_visit = [cfg[0]] if cfg else []

    while to_visit:
        block = to_visit.pop()
        if block not in reachable:
            reachable.add(block)
            to_visit.extend(block.successors)

    return [block for block in cfg if block not in reachable]


def compute_live_variables(tac):
    # Simplified: variables used after assignment
    live = set()

    for instr in reversed(tac):
        if instr[0] == 'assign':
            if instr[1] in live:
                live.remove(instr[1])
            mark_used(live, instr[2])
            if len(instr) > 4:
                mark_used(live, instr[4])
        elif instr[0] in ['if_false', 'return']:
            mark_used(live, instr[1])
        elif instr[0] == 'call':
            for arg in instr[2]:
                mark_used(live, arg)

    return live


def find_redundant_assignments(tac):
    assigned = set()
    redundant = []

    for i, instr in enumerate(tac):
        if instr[0] == 'assign':
            if instr[1] in assigned:
                redundant.append(i)
            assigned.add(instr[1])

    return redundant


def find_constant_conditions(tac):
    constants = []

    for i, instr in enumerate(tac):
        if instr[0] == 'if_false' and instr[1] in [0, 1]:
            constants.append(i)

    return constants
