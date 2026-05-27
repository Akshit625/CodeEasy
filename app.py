from flask import Flask, request, jsonify, render_template
from backend.parser import get_source_context, parse_code
from backend.tac import generate_tac
from backend.cfg import build_cfg
from backend.analysis import analyze_code
from backend.ast_optimizer import optimize_ast
from backend.optimizer import optimize_code
from backend.generator import generate_code, generate_tac_code

app = Flask(__name__, template_folder='frontend', static_folder='frontend')

def serialize_cfg(cfg):
    block_indexes = {id(block): index for index, block in enumerate(cfg)}
    nodes = []
    edges = []

    for index, block in enumerate(cfg):
        block_id = f'B{index + 1}'
        label = block.label or block_id
        nodes.append({
            'id': block_id,
            'label': label,
            'instructions': generate_tac_code(block.instructions)
        })

        last_instr = block.instructions[-1] if block.instructions else None
        for successor_index, successor in enumerate(block.successors):
            target_index = block_indexes[id(successor)]
            edges.append({
                'from': block_id,
                'to': f'B{target_index + 1}',
                'label': edge_label(last_instr, successor_index)
            })

    return {'nodes': nodes, 'edges': edges}


def edge_label(last_instr, successor_index):
    if not last_instr:
        return ''
    if last_instr[0] == 'if_false':
        return 'false' if successor_index == 0 else 'true'
    if last_instr[0] == 'jump':
        return 'goto'
    return 'next'


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    code = data['code']
    source_context = get_source_context(code)
    print("Received code:", repr(code))
    try:
        # Parse
        ast = parse_code(code)
        print("Parsed AST:", ast)
        # TAC
        tac = generate_tac(ast)
        print("TAC:", tac)
        tac_code = generate_tac_code(tac)
        # CFG
        cfg = build_cfg(tac)
        print("CFG:", cfg)
        cfg_graph = serialize_cfg(cfg)
        # Analysis
        analysis = analyze_code(tac, cfg)
        print("Analysis:", analysis)
        # Optimize
        optimized_tac = optimize_code(tac, analysis)
        print("Optimized TAC:", optimized_tac)
        optimized_tac_code = generate_tac_code(optimized_tac)
        optimized_ast = optimize_ast(ast)
        print("Optimized AST:", optimized_ast)
        # Generate code
        optimized_code = generate_code(optimized_ast, source_context)
        print("Optimized code:", repr(optimized_code))
        return jsonify({
            'success': True,
            'optimized': optimized_code,
            'tac': tac_code,
            'optimized_tac': optimized_tac_code,
            'cfg': cfg_graph
        })
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
