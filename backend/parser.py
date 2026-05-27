import re

import ply.lex as lex
import ply.yacc as yacc

# Tokens
tokens = (
    'ID', 'NUMBER', 'STRING',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'INCREMENT',
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    'SEMICOLON', 'COMMA', 'ASSIGN',
    'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
    'IF', 'ELSE', 'WHILE', 'FOR', 'BREAK', 'RETURN', 'INT',
    'TRUE', 'FALSE'
)

# Reserved words
reserved = {
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'for': 'FOR',
    'break': 'BREAK',
    'return': 'RETURN',
    'int': 'INT',
    'true': 'TRUE',
    'false': 'FALSE'
}

# Token definitions
t_PLUS = r'\+'
t_INCREMENT = r'\+\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_SEMICOLON = r';'
t_COMMA = r','
t_ASSIGN = r'='
t_EQ = r'=='
t_NE = r'!='
t_LE = r'<='
t_LT = r'<'
t_GE = r'>='
t_GT = r'>'


def t_BLOCK_COMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')


def t_LINE_COMMENT(t):
    r'//[^\n]*'
    pass


def t_DIVIDE(t):
    r'/'
    return t


def t_STRING(t):
    r'"([^"\\]|\\.)*"'
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t


t_ignore = ' \t'


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_error(t):
    raise SyntaxError(f"Illegal character '{t.value[0]}'")


lexer = lex.lex()

precedence = (
    ('left', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
)


def p_program(p):
    '''program : statements'''
    p[0] = p[1]


def p_statements_single(p):
    '''statements : statement'''
    p[0] = p[1]


def p_statements_multiple(p):
    '''statements : statements statement'''
    p[0] = p[1] + p[2]


def p_statement(p):
    '''statement : declaration
                 | assignment
                 | if_stmt
                 | while_stmt
                 | for_stmt
                 | break_stmt
                 | return_stmt
                 | call_stmt'''
    p[0] = p[1]


def p_declaration(p):
    '''declaration : INT declarator_list SEMICOLON'''
    p[0] = [('declare', p[2])]


def p_declarator_list_single(p):
    '''declarator_list : declarator'''
    p[0] = p[1]


def p_declarator_list_multiple(p):
    '''declarator_list : declarator_list COMMA declarator'''
    p[0] = p[1] + p[3]


def p_declarator(p):
    '''declarator : ID
                  | ID ASSIGN expression'''
    if len(p) == 2:
        p[0] = [(p[1], None)]
    else:
        p[0] = [(p[1], p[3])]


def p_assignment(p):
    '''assignment : ID ASSIGN expression SEMICOLON'''
    p[0] = [('assign', p[1], p[3])]


def p_block(p):
    '''block : LBRACE statements_opt RBRACE'''
    p[0] = p[2]


def p_statements_opt(p):
    '''statements_opt : empty
                      | statements'''
    p[0] = p[1]


def p_if_stmt_if(p):
    '''if_stmt : IF LPAREN expression RPAREN block'''
    p[0] = [('if', p[3], p[5])]


def p_if_stmt_else_block(p):
    '''if_stmt : IF LPAREN expression RPAREN block ELSE block'''
    p[0] = [('if-else', p[3], p[5], p[7])]


def p_if_stmt_else_if(p):
    '''if_stmt : IF LPAREN expression RPAREN block ELSE if_stmt'''
    p[0] = [('if-else', p[3], p[5], p[7])]


def p_while_stmt(p):
    '''while_stmt : WHILE LPAREN expression RPAREN block'''
    p[0] = [('while', p[3], p[5])]


def p_for_stmt(p):
    '''for_stmt : FOR LPAREN for_init SEMICOLON for_condition SEMICOLON for_update RPAREN block'''
    p[0] = [('for', p[3], p[5], p[7], p[9])]


def p_for_init(p):
    '''for_init : empty
                | declaration_head
                | assignment_head'''
    p[0] = p[1]


def p_for_condition(p):
    '''for_condition : empty
                     | expression'''
    p[0] = 1 if p[1] == [] else p[1]


def p_for_update(p):
    '''for_update : empty
                  | assignment_head
                  | increment_head'''
    p[0] = p[1]


def p_declaration_head(p):
    '''declaration_head : INT declarator_list'''
    p[0] = [('declare', p[2])]


def p_assignment_head(p):
    '''assignment_head : ID ASSIGN expression'''
    p[0] = [('assign', p[1], p[3])]


def p_increment_head(p):
    '''increment_head : ID INCREMENT'''
    p[0] = [('assign', p[1], (p[1], '+', 1))]


def p_break_stmt(p):
    '''break_stmt : BREAK SEMICOLON'''
    p[0] = [('break',)]


def p_return_stmt(p):
    '''return_stmt : RETURN expression SEMICOLON'''
    p[0] = [('return', p[2])]


def p_call_stmt(p):
    '''call_stmt : ID LPAREN arguments_opt RPAREN SEMICOLON'''
    p[0] = [('call', p[1], p[3])]


def p_arguments_opt(p):
    '''arguments_opt : empty
                     | arguments'''
    p[0] = p[1]


def p_arguments_single(p):
    '''arguments : expression'''
    p[0] = [p[1]]


def p_arguments_multiple(p):
    '''arguments : arguments COMMA expression'''
    p[0] = p[1] + [p[3]]


def p_expression_binop(p):
    '''expression : expression PLUS term
                  | expression MINUS term
                  | expression EQ term
                  | expression NE term
                  | expression LT term
                  | expression LE term
                  | expression GT term
                  | expression GE term'''
    p[0] = (p[1], p[2], p[3])


def p_expression_term(p):
    '''expression : term'''
    p[0] = p[1]


def p_term_binop(p):
    '''term : term TIMES factor
            | term DIVIDE factor'''
    p[0] = (p[1], p[2], p[3])


def p_term_factor(p):
    '''term : factor'''
    p[0] = p[1]


def p_factor(p):
    '''factor : NUMBER
              | STRING
              | ID
              | TRUE
              | FALSE
              | LPAREN expression RPAREN'''
    if len(p) == 2:
        if p.slice[1].type == 'TRUE':
            p[0] = 1
        elif p.slice[1].type == 'FALSE':
            p[0] = 0
        else:
            p[0] = p[1]
    else:
        p[0] = p[2]


def p_empty(p):
    'empty :'
    p[0] = []


def p_error(p):
    if p is None:
        raise SyntaxError('Syntax error at end of input')
    raise SyntaxError(f"Syntax error at '{p.value}'")


parser = yacc.yacc()


def _strip_preprocessor_lines(code):
    return re.sub(r'^\s*#.*$', '', code, flags=re.MULTILINE)


def _extract_main_body(code):
    match = re.search(r'\bint\s+main\s*\(\s*\)\s*\{', code)
    if not match:
        return code

    start = match.end() - 1
    depth = 0

    for index in range(start, len(code)):
        char = code[index]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return code[start + 1:index]

    raise SyntaxError('Unmatched braces in main function')


def preprocess_code(code):
    cleaned = _strip_preprocessor_lines(code)
    cleaned = _extract_main_body(cleaned)
    return cleaned.strip()


def get_source_context(code):
    includes = re.findall(r'^\s*#.*$', code, flags=re.MULTILINE)
    has_main = re.search(r'\bint\s+main\s*\(\s*\)\s*\{', code) is not None
    return {
        'includes': includes,
        'wrap_main': has_main
    }


def parse_code(code):
    cleaned = preprocess_code(code)
    lexer.lineno = 1
    result = parser.parse(cleaned, lexer=lexer)
    if result is None:
        raise SyntaxError('Unable to parse input code')
    return result
