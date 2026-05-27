class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0
        self.loop_end_stack = []

    def new_temp(self):
        self.temp_count += 1
        return f't{self.temp_count}'

    def new_label(self):
        self.label_count += 1
        return f'L{self.label_count}'

    def generate(self, ast):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0
        self.loop_end_stack = []
        self.generate_statements(ast)
        return self.instructions

    def generate_statements(self, statements):
        for stmt in statements:
            self.generate_statement(stmt)

    def generate_statement(self, stmt):
        if stmt[0] == 'declare':
            for name, initializer in stmt[1]:
                if initializer is not None:
                    expr = self.generate_expression(initializer)
                    self.instructions.append(('assign', name, expr))
        elif stmt[0] == 'assign':
            expr = self.generate_expression(stmt[2])
            self.instructions.append(('assign', stmt[1], expr))
        elif stmt[0] == 'call':
            args = [self.generate_expression(arg) for arg in stmt[2]]
            self.instructions.append(('call', stmt[1], args))
        elif stmt[0] == 'if':
            cond = self.generate_expression(stmt[1])
            label_end = self.new_label()
            self.instructions.append(('if_false', cond, label_end))
            self.generate_statements(stmt[2])
            self.instructions.append(('label', label_end))
        elif stmt[0] == 'if-else':
            cond = self.generate_expression(stmt[1])
            label_else = self.new_label()
            label_end = self.new_label()
            self.instructions.append(('if_false', cond, label_else))
            self.generate_statements(stmt[2])
            self.instructions.append(('jump', label_end))
            self.instructions.append(('label', label_else))
            self.generate_statements(stmt[3])
            self.instructions.append(('label', label_end))
        elif stmt[0] == 'while':
            label_start = self.new_label()
            label_end = self.new_label()
            self.instructions.append(('label', label_start))
            cond = self.generate_expression(stmt[1])
            self.instructions.append(('if_false', cond, label_end))
            self.loop_end_stack.append(label_end)
            self.generate_statements(stmt[2])
            self.loop_end_stack.pop()
            self.instructions.append(('jump', label_start))
            self.instructions.append(('label', label_end))
        elif stmt[0] == 'for':
            label_start = self.new_label()
            label_end = self.new_label()
            self.generate_statements(stmt[1])
            self.instructions.append(('label', label_start))
            cond = self.generate_expression(stmt[2])
            self.instructions.append(('if_false', cond, label_end))
            self.loop_end_stack.append(label_end)
            self.generate_statements(stmt[4])
            self.loop_end_stack.pop()
            self.generate_statements(stmt[3])
            self.instructions.append(('jump', label_start))
            self.instructions.append(('label', label_end))
        elif stmt[0] == 'break':
            if not self.loop_end_stack:
                raise SyntaxError('break used outside of a loop')
            self.instructions.append(('jump', self.loop_end_stack[-1]))
        elif stmt[0] == 'return':
            expr = self.generate_expression(stmt[1])
            self.instructions.append(('return', expr))

    def generate_expression(self, expr):
        if isinstance(expr, int) or isinstance(expr, str):
            return expr
        elif len(expr) == 3 and expr[1] in ['+', '-', '*', '/', '==', '!=', '<', '<=', '>', '>=']:
            left = self.generate_expression(expr[0])
            right = self.generate_expression(expr[2])
            temp = self.new_temp()
            self.instructions.append(('assign', temp, left, expr[1], right))
            return temp
        else:
            return expr  # For simple cases

def generate_tac(ast):
    generator = TACGenerator()
    return generator.generate(ast)
