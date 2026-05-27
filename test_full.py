from backend.parser import parse_code
from backend.tac import generate_tac
from backend.cfg import build_cfg
from backend.analysis import analyze_code
from backend.optimizer import optimize_code
from backend.generator import generate_code

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
    print("AST:", ast)
    tac = generate_tac(ast)
    print("TAC:", tac)
    cfg = build_cfg(tac)
    print("CFG blocks:", len(cfg))
    analysis = analyze_code(tac, cfg)
    print("Analysis:", analysis)
    optimized_tac = optimize_code(tac, analysis)
    print("Optimized TAC:", optimized_tac)
    optimized_code = generate_code(optimized_tac)
    print("Optimized code:", optimized_code)
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()