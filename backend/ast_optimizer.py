def optimize_ast(statements):
    simplified = simplify_statements(statements)
    optimized, _, _ = eliminate_dead_code(simplified, set())
    return fold_declaration_initializers(optimized)


def simplify_statements(statements, assumptions=None, constants=None):
    assumptions = assumptions or []
    constants = {} if constants is None else constants
    simplified = []

    for stmt in statements:
        kind = stmt[0]

        if kind == 'declare':
            declarators = []
            for name, initializer in stmt[1]:
                simplified_initializer = simplify_expression(initializer, constants)
                constant_initializer = simplify_expression(initializer, constants, use_constants=True)
                declarators.append((name, simplified_initializer))
                update_constant(constants, name, constant_initializer)
            simplified.append(('declare', declarators))
        elif kind == 'assign':
            value = simplify_expression(stmt[2], constants)
            simplified.append(('assign', stmt[1], value))
            update_constant(constants, stmt[1], simplify_expression(stmt[2], constants, use_constants=True))
        elif kind == 'call':
            simplified.append(('call', stmt[1], [simplify_expression(arg, constants) for arg in stmt[2]]))
        elif kind == 'return':
            simplified.append(('return', simplify_expression(stmt[1], constants)))
            break
        elif kind == 'break':
            simplified.append(stmt)
            break
        elif kind == 'if':
            condition = simplify_expression(stmt[1], constants)
            evaluated_condition = simplify_expression(stmt[1], constants, use_constants=True)
            truth = evaluate_condition(evaluated_condition, assumptions)

            if truth == 0:
                continue
            if truth == 1:
                body = simplify_statements(stmt[2], assumptions + [condition], constants)
                simplified.extend(body)
                if block_terminates(body):
                    break
                continue
            body_constants = constants.copy()
            body = simplify_statements(stmt[2], assumptions + [condition], body_constants)
            if body:
                simplified.append(('if', condition, body))
                remove_constants(constants, assigned_variables(stmt[2]))
        elif kind == 'if-else':
            condition = simplify_expression(stmt[1], constants)
            evaluated_condition = simplify_expression(stmt[1], constants, use_constants=True)
            truth = evaluate_condition(evaluated_condition, assumptions)

            if truth == 1:
                then_body = simplify_statements(stmt[2], assumptions + [condition], constants)
                simplified.extend(then_body)
                if block_terminates(then_body):
                    break
                continue
            if truth == 0:
                else_body = simplify_statements(stmt[3], assumptions + [invert_condition(condition)], constants)
                simplified.extend(else_body)
                if block_terminates(else_body):
                    break
                continue

            then_constants = constants.copy()
            else_constants = constants.copy()
            then_body = simplify_statements(stmt[2], assumptions + [condition], then_constants)
            else_body = simplify_statements(stmt[3], assumptions + [invert_condition(condition)], else_constants)

            if then_body and else_body:
                simplified.append(('if-else', condition, then_body, else_body))
                constants.clear()
                constants.update(merge_constants(then_constants, else_constants))
                if block_terminates(then_body) and block_terminates(else_body):
                    break
            elif then_body:
                simplified.append(('if', condition, then_body))
                remove_constants(constants, assigned_variables(stmt[2]))
            elif else_body:
                simplified.append(('if', invert_condition(condition), else_body))
                remove_constants(constants, assigned_variables(stmt[3]))
        elif kind == 'while':
            body_assignments = assigned_variables(stmt[2])
            condition_constants = constants_without(constants, body_assignments)
            condition = simplify_expression(stmt[1], condition_constants)
            evaluated_condition = simplify_expression(stmt[1], condition_constants, use_constants=True)
            truth = evaluate_condition(evaluated_condition, assumptions)

            if truth == 0:
                continue
            body = simplify_statements(stmt[2], assumptions + [condition], constants.copy())
            simplified.append(('while', condition, body))
            remove_constants(constants, body_assignments)
        elif kind == 'for':
            init = simplify_statements(stmt[1], assumptions, constants)
            condition = simplify_expression(stmt[2], constants)
            evaluated_condition = simplify_expression(stmt[2], constants, use_constants=True)
            loop_assignments = assigned_variables(stmt[3]) | assigned_variables(stmt[4])
            loop_constants = constants_without(constants, loop_assignments)
            update = simplify_statements(stmt[3], assumptions + [condition], loop_constants.copy())
            body = simplify_statements(stmt[4], assumptions + [condition], loop_constants.copy())

            if evaluate_condition(evaluated_condition, assumptions) == 0:
                simplified.extend(init)
                continue

            simplified.append(('for', init, condition, update, body))
            remove_constants(constants, loop_assignments)

    return simplified


def eliminate_dead_code(statements, live_after):
    optimized_reversed = []
    live = set(live_after)
    required_declarations = set(live_after)

    for stmt in reversed(statements):
        kind = stmt[0]

        if kind == 'return':
            optimized_reversed.append(stmt)
            live = expression_variables(stmt[1])
            required_declarations |= live
        elif kind == 'break':
            optimized_reversed.append(stmt)
            live = set()
        elif kind == 'call':
            optimized_reversed.append(stmt)
            call_vars = expression_list_variables(stmt[2])
            live |= call_vars
            required_declarations |= call_vars
        elif kind == 'assign':
            if stmt[1] in live:
                optimized_reversed.append(stmt)
                required_declarations.add(stmt[1])
                live.discard(stmt[1])
                expr_vars = expression_variables(stmt[2])
                live |= expr_vars
                required_declarations |= expr_vars
        elif kind == 'declare':
            kept = []
            current_live = set(live)
            current_required = set(required_declarations)

            for name, initializer in reversed(stmt[1]):
                declaration_needed = name in current_required or name in current_live
                value_needed = name in current_live

                if declaration_needed:
                    kept_initializer = initializer if value_needed else None
                    kept.append((name, kept_initializer))
                    current_live.discard(name)
                    current_required.discard(name)
                    if value_needed and initializer is not None:
                        init_vars = expression_variables(initializer)
                        current_live |= init_vars
                        current_required |= init_vars

            live = current_live
            required_declarations = current_required
            if kept:
                optimized_reversed.append(('declare', list(reversed(kept))))
        elif kind == 'if':
            body, body_live, body_required = eliminate_dead_code(stmt[2], live)
            if body:
                optimized_reversed.append(('if', stmt[1], body))
                cond_vars = expression_variables(stmt[1])
                live = live | body_live | cond_vars
                required_declarations |= body_required | cond_vars
        elif kind == 'if-else':
            then_body, then_live, then_required = eliminate_dead_code(stmt[2], live)
            else_body, else_live, else_required = eliminate_dead_code(stmt[3], live)

            if then_body and else_body:
                optimized_reversed.append(('if-else', stmt[1], then_body, else_body))
                cond_vars = expression_variables(stmt[1])
                live = then_live | else_live | cond_vars
                required_declarations |= then_required | else_required | cond_vars
            elif then_body:
                optimized_reversed.append(('if', stmt[1], then_body))
                cond_vars = expression_variables(stmt[1])
                live = then_live | live | cond_vars
                required_declarations |= then_required | cond_vars
            elif else_body:
                optimized_reversed.append(('if', invert_condition(stmt[1]), else_body))
                cond_vars = expression_variables(stmt[1])
                live = else_live | live | cond_vars
                required_declarations |= else_required | cond_vars
        elif kind == 'while':
            cond_vars = expression_variables(stmt[1])
            body, body_live, body_required = eliminate_dead_code(stmt[2], live | cond_vars)
            optimized_reversed.append(('while', stmt[1], body))
            live = live | body_live | cond_vars
            required_declarations |= body_required | cond_vars
        elif kind == 'for':
            cond_vars = expression_variables(stmt[2])
            update_vars = statement_variables(stmt[3])
            body, body_live, body_required = eliminate_dead_code(stmt[4], live | cond_vars | update_vars)
            update, update_live, update_required = eliminate_dead_code(stmt[3], live | cond_vars | body_live)
            init, init_live, init_required = eliminate_dead_code(
                stmt[1],
                cond_vars | update_vars | update_live | body_live
            )

            optimized_reversed.append(('for', init, stmt[2], update, body))
            live = live | cond_vars | body_live | update_live | init_live
            required_declarations |= cond_vars | body_required | update_required | init_required

    return list(reversed(optimized_reversed)), live, required_declarations


def fold_declaration_initializers(statements):
    folded = []
    index = 0

    while index < len(statements):
        stmt = statements[index]
        kind = stmt[0]

        if kind == 'declare':
            declarators = list(stmt[1])
            next_index = index + 1

            while next_index < len(statements):
                next_stmt = statements[next_index]
                if next_stmt[0] != 'assign':
                    break

                target = next_stmt[1]
                match_index = None

                for declarator_index, (name, initializer) in enumerate(declarators):
                    if name == target and initializer is None:
                        match_index = declarator_index
                        break

                if match_index is None:
                    break

                declarators[match_index] = (target, next_stmt[2])
                next_index += 1

            folded.append(('declare', declarators))
            index = next_index
            continue

        if kind == 'if':
            folded.append(('if', stmt[1], fold_declaration_initializers(stmt[2])))
        elif kind == 'if-else':
            folded.append((
                'if-else',
                stmt[1],
                fold_declaration_initializers(stmt[2]),
                fold_declaration_initializers(stmt[3])
            ))
        elif kind == 'while':
            folded.append(('while', stmt[1], fold_declaration_initializers(stmt[2])))
        elif kind == 'for':
            folded.append((
                'for',
                fold_declaration_initializers(stmt[1]),
                stmt[2],
                fold_declaration_initializers(stmt[3]),
                fold_declaration_initializers(stmt[4])
            ))
        else:
            folded.append(stmt)

        index += 1

    return folded


def block_returns(statements):
    return bool(statements) and statements[-1][0] == 'return'


def block_terminates(statements):
    return bool(statements) and statements[-1][0] in {'break', 'return'}


def update_constant(constants, name, value):
    if isinstance(value, int):
        constants[name] = value
    else:
        constants.pop(name, None)


def remove_constants(constants, names):
    for name in names:
        constants.pop(name, None)


def constants_without(constants, names):
    return {
        name: value
        for name, value in constants.items()
        if name not in names
    }


def merge_constants(left, right):
    return {
        name: value
        for name, value in left.items()
        if name in right and right[name] == value
    }


def simplify_expression(expr, constants=None, use_constants=False):
    constants = constants or {}

    if isinstance(expr, str):
        if expr.startswith('"') and expr.endswith('"'):
            return expr
        if use_constants:
            return constants.get(expr, expr)
        return expr

    if isinstance(expr, tuple) and len(expr) == 3:
        left = simplify_expression(expr[0], constants, use_constants)
        op = expr[1]
        right = simplify_expression(expr[2], constants, use_constants)
        constant = evaluate_constant((left, op, right))
        if constant is not None:
            return constant
        return (left, op, right)
    return expr


def evaluate_constant(expr):
    if isinstance(expr, int):
        return expr

    if not (isinstance(expr, tuple) and len(expr) == 3):
        return None

    left = evaluate_constant(expr[0])
    right = evaluate_constant(expr[2])

    if left is None or right is None:
        return None

    op = expr[1]

    if op == '+':
        return left + right
    if op == '-':
        return left - right
    if op == '*':
        return left * right
    if op == '/':
        if right == 0:
            return None
        return left // right
    if op == '==':
        return int(left == right)
    if op == '!=':
        return int(left != right)
    if op == '<':
        return int(left < right)
    if op == '<=':
        return int(left <= right)
    if op == '>':
        return int(left > right)
    if op == '>=':
        return int(left >= right)

    return None


def evaluate_condition(expr, assumptions):
    constant = evaluate_constant(expr)
    if constant is not None:
        return int(bool(constant))

    if is_condition_impossible(expr, assumptions):
        return 0

    if is_condition_guaranteed(expr, assumptions):
        return 1

    return None


def is_condition_impossible(expr, assumptions):
    target = extract_constraint(expr)
    if target is None:
        return False

    for assumption in assumptions:
        constraint = extract_constraint(assumption)
        if constraint is None:
            continue
        if constraints_contradict(constraint, target):
            return True

    return False


def is_condition_guaranteed(expr, assumptions):
    target = extract_constraint(expr)
    if target is None:
        return False

    for assumption in assumptions:
        constraint = extract_constraint(assumption)
        if constraint is None:
            continue
        if constraint_implies(constraint, target):
            return True

    return False


def extract_constraint(expr):
    if not (isinstance(expr, tuple) and len(expr) == 3):
        return None

    left, op, right = expr
    if isinstance(left, str) and isinstance(right, int):
        return (left, op, right)
    if isinstance(left, int) and isinstance(right, str):
        flipped = {
            '<': '>',
            '<=': '>=',
            '>': '<',
            '>=': '<=',
            '==': '==',
            '!=': '!='
        }
        return (right, flipped.get(op, op), left)
    return None


def constraints_contradict(left, right):
    if left[0] != right[0]:
        return False
    return not ranges_overlap(constraint_range(left), constraint_range(right))


def constraint_implies(left, right):
    if left[0] != right[0]:
        return False
    left_range = constraint_range(left)
    right_range = constraint_range(right)
    return range_subset(left_range, right_range)


def constraint_range(constraint):
    _, op, value = constraint
    if op == '>':
        return (value + 1, None, True)
    if op == '>=':
        return (value, None, True)
    if op == '<':
        return (None, value - 1, True)
    if op == '<=':
        return (None, value, True)
    if op == '==':
        return (value, value, False)
    if op == '!=':
        return (None, None, False, value)
    return (None, None, True)


def ranges_overlap(left_range, right_range):
    left_forbidden = left_range[3] if len(left_range) > 3 else None
    right_forbidden = right_range[3] if len(right_range) > 3 else None

    if left_forbidden is not None:
        return not range_subset(right_range, (left_forbidden, left_forbidden, False))
    if right_forbidden is not None:
        return not range_subset(left_range, (right_forbidden, right_forbidden, False))

    lower = max_bound(left_range[0], right_range[0], minimum=True)
    upper = min_bound(left_range[1], right_range[1], minimum=False)

    if lower is None or upper is None:
        return True

    return lower <= upper


def range_subset(left_range, right_range):
    left_forbidden = left_range[3] if len(left_range) > 3 else None
    right_forbidden = right_range[3] if len(right_range) > 3 else None

    if left_forbidden is not None:
        return False
    if right_forbidden is not None:
        if left_range[0] == left_range[1] == right_forbidden:
            return False
        return True

    left_lower, left_upper = left_range[0], left_range[1]
    right_lower, right_upper = right_range[0], right_range[1]

    lower_ok = right_lower is None or (left_lower is not None and left_lower >= right_lower)
    upper_ok = right_upper is None or (left_upper is not None and left_upper <= right_upper)
    return lower_ok and upper_ok


def max_bound(left, right, minimum=True):
    bounds = [bound for bound in [left, right] if bound is not None]
    if not bounds:
        return None
    return max(bounds)


def min_bound(left, right, minimum=False):
    bounds = [bound for bound in [left, right] if bound is not None]
    if not bounds:
        return None
    return min(bounds)


def invert_condition(expr):
    if isinstance(expr, int):
        return 0 if expr else 1

    if isinstance(expr, tuple) and len(expr) == 3:
        inverse_ops = {
            '==': '!=',
            '!=': '==',
            '<': '>=',
            '<=': '>',
            '>': '<=',
            '>=': '<'
        }
        if expr[1] in inverse_ops:
            return (expr[0], inverse_ops[expr[1]], expr[2])

    return (expr, '==', 0)


def expression_variables(expr):
    if isinstance(expr, str):
        if expr.startswith('"') and expr.endswith('"'):
            return set()
        return {expr}
    if isinstance(expr, tuple) and len(expr) == 3:
        return expression_variables(expr[0]) | expression_variables(expr[2])
    return set()


def expression_list_variables(expressions):
    variables = set()
    for expr in expressions:
        variables |= expression_variables(expr)
    return variables


def assigned_variables(statements):
    assigned = set()

    for stmt in statements:
        kind = stmt[0]
        if kind == 'declare':
            assigned.update(name for name, _ in stmt[1])
        elif kind == 'assign':
            assigned.add(stmt[1])
        elif kind in {'if', 'while'}:
            assigned |= assigned_variables(stmt[2])
        elif kind == 'if-else':
            assigned |= assigned_variables(stmt[2])
            assigned |= assigned_variables(stmt[3])
        elif kind == 'for':
            assigned |= assigned_variables(stmt[1])
            assigned |= assigned_variables(stmt[3])
            assigned |= assigned_variables(stmt[4])

    return assigned


def statement_variables(statements):
    variables = set()

    for stmt in statements:
        kind = stmt[0]
        if kind == 'declare':
            for name, initializer in stmt[1]:
                variables.add(name)
                if initializer is not None:
                    variables |= expression_variables(initializer)
        elif kind == 'assign':
            variables.add(stmt[1])
            variables |= expression_variables(stmt[2])
        elif kind == 'call':
            variables |= expression_list_variables(stmt[2])
        elif kind == 'return':
            variables |= expression_variables(stmt[1])
        elif kind in {'if', 'while'}:
            variables |= expression_variables(stmt[1])
            variables |= statement_variables(stmt[2])
        elif kind == 'if-else':
            variables |= expression_variables(stmt[1])
            variables |= statement_variables(stmt[2])
            variables |= statement_variables(stmt[3])
        elif kind == 'for':
            variables |= statement_variables(stmt[1])
            variables |= expression_variables(stmt[2])
            variables |= statement_variables(stmt[3])
            variables |= statement_variables(stmt[4])

    return variables
