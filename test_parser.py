from backend.parser import parse_code

code = """int x;
int y;
int z;
x = 5;
y = 10;
z = x + y;
x = 20;
if (false) {
    y = 30;
    z = 40;
}
return x;"""

try:
    ast = parse_code(code)
    print("Parsed AST:", ast)
except Exception as e:
    print("Parse error:", e)