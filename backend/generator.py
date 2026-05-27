PRECEDENCE = {
    '==': 1,
    '!=': 1,
    '<': 1,
    '<=': 1,
    '>': 1,
    '>=': 1,
    '+': 2,
    '-': 2,
    '*': 3,
    '/': 3
}


def generate_code(program, source_context=None):
    if not program:
        return ''

    if is_ast(program):
        return generate_ast_code(program, source_context or {})

    return generate_tac_code(program)


def is_ast(program):
    ast_kinds = {'declare', 'assign', 'if', 'if-else', 'while', 'for', 'break', 'call', 'return'}
    return isinstance(program, list) and isinstance(program[0], tuple) and program[0][0] in ast_kinds


def generate_ast_code(statements, source_context):
    lines = []
    includes = source_context.get('includes', [])
    wrap_main = source_context.get('wrap_main', False)

    if includes:
        lines.extend(includes)
        lines.append('')

    if wrap_main:
        lines.append('int main() {')
        body = render_statements(statements, 1)
        lines.extend(body)
        lines.append('}')
    else:
        lines.extend(render_statements(statements, 0))

    return '\n'.join(lines)


def render_statements(statements, indent_level):
    lines = []

    for index, stmt in enumerate(statements):
        kind = stmt[0]

        if index > 0 and should_insert_blank_line(statements[index - 1], stmt):
            lines.append('')

        if kind == 'declare':
            declarators = []
            for name, initializer in stmt[1]:
                if initializer is None:
                    declarators.append(name)
                else:
                    declarators.append(f'{name} = {format_expression(initializer)}')
            lines.append(indent(indent_level) + f"int {', '.join(declarators)};")
        elif kind == 'assign':
            lines.append(indent(indent_level) + f'{stmt[1]} = {format_expression(stmt[2])};')
        elif kind == 'call':
            arguments = ', '.join(format_expression(arg) for arg in stmt[2])
            lines.append(indent(indent_level) + f'{stmt[1]}({arguments});')
        elif kind == 'return':
            lines.append(indent(indent_level) + f'return {format_expression(stmt[1])};')
        elif kind == 'break':
            lines.append(indent(indent_level) + 'break;')
        elif kind == 'if':
            lines.append(indent(indent_level) + f'if ({format_expression(stmt[1])}) {{')
            lines.extend(render_statements(stmt[2], indent_level + 1))
            lines.append(indent(indent_level) + '}')
        elif kind == 'if-else':
            lines.append(indent(indent_level) + f'if ({format_expression(stmt[1])}) {{')
            lines.extend(render_statements(stmt[2], indent_level + 1))
            else_branch = stmt[3]
            if len(else_branch) == 1 and else_branch[0][0] in {'if', 'if-else'}:
                nested = render_else_if_chain(else_branch[0], indent_level)
                lines.append(indent(indent_level) + '} else ' + nested[0].lstrip())
                lines.extend(nested[1:])
            else:
                lines.append(indent(indent_level) + '} else {')
                lines.extend(render_statements(else_branch, indent_level + 1))
                lines.append(indent(indent_level) + '}')
        elif kind == 'while':
            lines.append(indent(indent_level) + f'while ({format_expression(stmt[1])}) {{')
            lines.extend(render_statements(stmt[2], indent_level + 1))
            lines.append(indent(indent_level) + '}')
        elif kind == 'for':
            lines.append(
                indent(indent_level)
                + f'for ({format_for_header_part(stmt[1])}; '
                + f'{format_expression(stmt[2])}; '
                + f'{format_for_header_part(stmt[3])}) {{'
            )
            lines.extend(render_statements(stmt[4], indent_level + 1))
            lines.append(indent(indent_level) + '}')

    return lines


def should_insert_blank_line(previous, current):
    grouped_kinds = {'declare'}
    if previous[0] in grouped_kinds and current[0] in grouped_kinds:
        return False
    return previous[0] != current[0]


def format_expression(expr, parent_precedence=0):
    if isinstance(expr, tuple) and len(expr) == 3:
        left, op, right = expr
        precedence = PRECEDENCE.get(op, 0)
        rendered = (
            f'{format_expression(left, precedence)} '
            f'{op} '
            f'{format_expression(right, precedence + 1 if op in ["-", "/"] else precedence)}'
        )
        if precedence < parent_precedence:
            return f'({rendered})'
        return rendered
    return str(expr)


def indent(level):
    return '    ' * level


def format_for_header_part(statements):
    if not statements:
        return ''

    parts = []
    for stmt in statements:
        kind = stmt[0]
        if kind == 'declare':
            declarators = []
            for name, initializer in stmt[1]:
                if initializer is None:
                    declarators.append(name)
                else:
                    declarators.append(f'{name} = {format_expression(initializer)}')
            parts.append(f"int {', '.join(declarators)}")
        elif kind == 'assign':
            parts.append(f'{stmt[1]} = {format_expression(stmt[2])}')
        elif kind == 'call':
            arguments = ', '.join(format_expression(arg) for arg in stmt[2])
            parts.append(f'{stmt[1]}({arguments})')

    return ', '.join(parts)


def render_else_if_chain(stmt, indent_level):
    kind = stmt[0]
    lines = [indent(indent_level) + f'if ({format_expression(stmt[1])}) {{']
    lines.extend(render_statements(stmt[2], indent_level + 1))

    if kind == 'if':
        lines.append(indent(indent_level) + '}')
        return lines

    else_branch = stmt[3]
    if len(else_branch) == 1 and else_branch[0][0] in {'if', 'if-else'}:
        nested = render_else_if_chain(else_branch[0], indent_level)
        lines.append(indent(indent_level) + '} else ' + nested[0].lstrip())
        lines.extend(nested[1:])
    else:
        lines.append(indent(indent_level) + '} else {')
        lines.extend(render_statements(else_branch, indent_level + 1))
        lines.append(indent(indent_level) + '}')

    return lines


def generate_tac_code(tac):
    code_lines = []

    for instr in tac:
        if instr[0] == 'assign':
            if len(instr) == 3:
                code_lines.append(f"{instr[1]} = {instr[2]};")
            elif len(instr) == 5:
                code_lines.append(f"{instr[1]} = {instr[2]} {instr[3]} {instr[4]};")
        elif instr[0] == 'if_false':
            code_lines.append(f"if_false {instr[1]} goto {instr[2]};")
        elif instr[0] == 'jump':
            code_lines.append(f"goto {instr[1]};")
        elif instr[0] == 'label':
            code_lines.append(f"{instr[1]}:")
        elif instr[0] == 'call':
            args = ', '.join(str(arg) for arg in instr[2])
            code_lines.append(f"{instr[1]}({args});")
        elif instr[0] == 'return':
            code_lines.append(f"return {instr[1]};")

    return '\n'.join(code_lines)
