import re


IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def optimize_code(tac, analysis):
    optimized = eliminate_constant_conditions(tac)
    optimized = remove_unreachable_code(optimized, analysis)
    optimized = remove_dead_assignments(optimized)
    optimized = remove_unused_labels(optimized)
    return optimized


def eliminate_constant_conditions(tac):
    optimized = []
    i = 0

    while i < len(tac):
        instr = tac[i]

        if instr[0] == 'if_false' and instr[1] in (0, 1):
            if instr[1] == 0:
                target_label = instr[2]
                i += 1
                while i < len(tac):
                    current = tac[i]
                    if current[0] == 'label' and current[1] == target_label:
                        break
                    i += 1
                continue

            i += 1
            continue

        optimized.append(instr)
        i += 1

    return optimized


def remove_unreachable_code(tac, analysis):
    optimized = tac[:]
    unreachable_indices = []

    for block in analysis['unreachable']:
        for instr in block.instructions:
            if instr in optimized:
                unreachable_indices.append(optimized.index(instr))

    for i in sorted(unreachable_indices, reverse=True):
        del optimized[i]

    return optimized


def is_identifier(value):
    return isinstance(value, str) and IDENTIFIER_PATTERN.fullmatch(value) is not None


def collect_used_values(tac):
    used = set()

    for instr in tac:
        if instr[0] == 'assign':
            mark_used(used, instr[2])
            if len(instr) > 4:
                mark_used(used, instr[4])
        elif instr[0] in ['if_false', 'return']:
            mark_used(used, instr[1])
        elif instr[0] == 'call':
            for arg in instr[2]:
                mark_used(used, arg)

    return used


def mark_used(used, value):
    if is_identifier(value):
        used.add(value)


def remove_dead_assignments(tac):
    optimized_reversed = []
    live = set()

    for instr in reversed(tac):
        if instr[0] == 'assign':
            target = instr[1]
            if target not in live:
                continue

            live.discard(target)
            mark_used(live, instr[2])
            if len(instr) > 4:
                mark_used(live, instr[4])
            optimized_reversed.append(instr)
        elif instr[0] == 'call':
            for arg in instr[2]:
                mark_used(live, arg)
            optimized_reversed.append(instr)
        elif instr[0] in ['if_false', 'return']:
            mark_used(live, instr[1])
            optimized_reversed.append(instr)
        else:
            optimized_reversed.append(instr)

    return list(reversed(optimized_reversed))


def remove_unused_labels(tac):
    referenced_labels = set()

    for instr in tac:
        if instr[0] == 'jump':
            referenced_labels.add(instr[1])
        elif instr[0] == 'if_false':
            referenced_labels.add(instr[2])

    return [
        instr for instr in tac
        if instr[0] != 'label' or instr[1] in referenced_labels
    ]
