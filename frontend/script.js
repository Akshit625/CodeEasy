document.getElementById('optimize-btn').addEventListener('click', async () => {
    const code = document.getElementById('input-code').value;
    console.log('Sending code:', code);
    try {
        const response = await fetch('/optimize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code })
        });
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Result:', result);
        if (result.success) {
            document.getElementById('output-code').textContent = result.optimized;
            document.getElementById('tac-code').textContent = addLineNumbers(result.tac || 'No TAC generated.');
            renderCfgGraph(result.cfg);
            alert('Optimization successful! Check the TAC, CFG, and output areas.');
        } else {
            document.getElementById('output-code').textContent = 'Error: ' + result.error;
            document.getElementById('tac-code').textContent = 'Error: ' + result.error;
            document.getElementById('cfg-graph').textContent = 'Error: ' + result.error;
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.log('Fetch error:', error);
        document.getElementById('output-code').textContent = 'Error: ' + error.message;
        document.getElementById('tac-code').textContent = 'Error: ' + error.message;
        document.getElementById('cfg-graph').textContent = 'Error: ' + error.message;
        alert('Fetch error: ' + error.message);
    }
});

function addLineNumbers(code) {
    return code
        .split('\n')
        .map((line, index) => `${String(index + 1).padStart(2, ' ')}  ${line}`)
        .join('\n');
}

function renderCfgGraph(cfg) {
    const graph = document.getElementById('cfg-graph');
    graph.textContent = '';

    if (!cfg || !cfg.nodes || cfg.nodes.length === 0) {
        graph.textContent = 'No CFG generated.';
        return;
    }

    const layout = buildCfgLayout(cfg);
    const nodePositions = layout.nodePositions;
    const svg = createSvgElement('svg', {
        viewBox: `0 0 ${layout.width} ${layout.height}`,
        role: 'img',
        'aria-label': 'Control flow graph'
    });

    svg.appendChild(createArrowMarkers());
    drawCfgLegend(svg, layout.width);

    cfg.edges.forEach((edge, index) => {
        drawEdge(svg, edge, index, nodePositions, layout);
    });

    cfg.nodes.forEach((node) => {
        drawNode(svg, node, nodePositions[node.id], layout.nodePadding, layout.lineHeight);
    });

    graph.appendChild(svg);
}

function buildCfgLayout(cfg) {
    const nodeWidth = 340;
    const columnGap = 90;
    const rowGap = 115;
    const leftMargin = 70;
    const rightMargin = 140;
    const topMargin = 75;
    const bottomMargin = 45;
    const lineHeight = 18;
    const nodePadding = 16;
    const maxLineLength = 38;
    const depths = getNodeDepths(cfg);
    const levels = [];
    const nodePositions = {};

    cfg.nodes.forEach((node) => {
        const depth = depths[node.id] || 0;
        if (!levels[depth]) {
            levels[depth] = [];
        }
        node.renderLines = buildNodeLines(node, maxLineLength);
        node.height = Math.max(92, 46 + node.renderLines.length * lineHeight);
        levels[depth].push(node);
    });

    const maxColumns = Math.max(...levels.filter(Boolean).map((level) => level.length), 1);
    const contentWidth = maxColumns * nodeWidth + (maxColumns - 1) * columnGap;
    const svgWidth = leftMargin + contentWidth + rightMargin;
    let currentY = topMargin;

    levels.forEach((level, depth) => {
        if (!level) {
            return;
        }

        const levelWidth = level.length * nodeWidth + (level.length - 1) * columnGap;
        let currentX = leftMargin + (contentWidth - levelWidth) / 2;
        const levelHeight = Math.max(...level.map((node) => node.height));

        level.forEach((node) => {
            nodePositions[node.id] = {
                x: currentX,
                y: currentY,
                width: nodeWidth,
                height: node.height,
                depth
            };
            currentX += nodeWidth + columnGap;
        });

        currentY += levelHeight + rowGap;
    });

    return {
        width: svgWidth,
        height: Math.max(currentY - rowGap + bottomMargin, 320),
        nodePositions,
        lineHeight,
        nodePadding,
        rightLaneX: svgWidth - rightMargin / 2
    };
}

function getNodeDepths(cfg) {
    const depths = {};
    const outgoing = {};

    cfg.nodes.forEach((node) => {
        outgoing[node.id] = [];
    });
    cfg.edges.forEach((edge) => {
        if (outgoing[edge.from]) {
            outgoing[edge.from].push(edge.to);
        }
    });

    const firstNode = cfg.nodes[0];
    if (!firstNode) {
        return depths;
    }

    depths[firstNode.id] = 0;
    const queue = [firstNode.id];

    while (queue.length > 0) {
        const nodeId = queue.shift();
        const nextDepth = depths[nodeId] + 1;

        outgoing[nodeId].forEach((targetId) => {
            if (depths[targetId] === undefined) {
                depths[targetId] = nextDepth;
                queue.push(targetId);
            }
        });
    }

    cfg.nodes.forEach((node, index) => {
        if (depths[node.id] === undefined) {
            depths[node.id] = index;
        }
    });

    return depths;
}

function buildNodeLines(node, maxLineLength) {
    const lines = node.instructions ? node.instructions.split('\n') : ['empty'];
    const wrapped = [];

    lines.forEach((line) => {
        wrapped.push(...wrapLine(line || ' ', maxLineLength));
    });

    return wrapped;
}

function wrapLine(line, maxLineLength) {
    if (line.length <= maxLineLength) {
        return [line];
    }

    const chunks = [];
    for (let index = 0; index < line.length; index += maxLineLength) {
        chunks.push((index === 0 ? '' : '  ') + line.slice(index, index + maxLineLength));
    }
    return chunks;
}

function drawNode(svg, node, position, padding, lineHeight) {
    const group = createSvgElement('g');
    const rect = createSvgElement('rect', {
        x: String(position.x),
        y: String(position.y),
        width: String(position.width),
        height: String(position.height),
        rx: '8',
        class: 'cfg-node'
    });
    group.appendChild(rect);

    const header = createSvgElement('rect', {
        x: String(position.x),
        y: String(position.y),
        width: String(position.width),
        height: '36',
        rx: '8',
        class: 'cfg-node-header'
    });
    group.appendChild(header);

    const title = createSvgElement('text', {
        x: String(position.x + padding),
        y: String(position.y + 26),
        class: 'cfg-node-title'
    });
    title.textContent = `${node.id}: ${node.label}`;
    group.appendChild(title);

    const instructions = node.renderLines || buildNodeLines(node, 38);
    instructions.forEach((line, index) => {
        const text = createSvgElement('text', {
            x: String(position.x + padding),
            y: String(position.y + 52 + index * lineHeight),
            class: 'cfg-node-code'
        });
        text.textContent = line || ' ';
        group.appendChild(text);
    });

    svg.appendChild(group);
}

function drawEdge(svg, edge, edgeIndex, nodePositions, layout) {
    const from = nodePositions[edge.from];
    const to = nodePositions[edge.to];

    if (!from || !to) {
        return;
    }

    const fromX = from.x + from.width / 2;
    const fromY = from.y + from.height;
    const toX = to.x + to.width / 2;
    const toY = to.y;
    const isBackEdge = to.depth <= from.depth;
    const skipsLevel = to.depth > from.depth + 1;
    const edgeKind = normalizeEdgeKind(edge.label);
    const laneX = layout.rightLaneX + edgeIndex * 6;

    let pathData;
    let labelX;
    let labelY;

    if (isBackEdge) {
        pathData = `M ${from.x + from.width} ${from.y + from.height / 2} L ${laneX} ${from.y + from.height / 2} L ${laneX} ${to.y + to.height / 2} L ${to.x + to.width} ${to.y + to.height / 2}`;
        labelX = laneX + 8;
        labelY = (from.y + to.y + to.height) / 2;
    } else if (skipsLevel) {
        pathData = `M ${from.x + from.width} ${from.y + from.height / 2} L ${laneX} ${from.y + from.height / 2} L ${laneX} ${toY - 24} L ${toX} ${toY - 24} L ${toX} ${toY}`;
        labelX = laneX + 8;
        labelY = (from.y + to.y) / 2;
    } else {
        const curveY = fromY + (toY - fromY) / 2;
        pathData = `M ${fromX} ${fromY} C ${fromX} ${curveY} ${toX} ${curveY} ${toX} ${toY}`;
        labelX = (fromX + toX) / 2 + 10;
        labelY = (fromY + toY) / 2;
    }

    const path = createSvgElement('path', {
        d: pathData,
        class: `cfg-edge cfg-edge-${edgeKind}`,
        'marker-end': `url(#arrowhead-${edgeKind})`
    });
    svg.appendChild(path);

    if (edge.label) {
        const label = createSvgElement('text', {
            x: String(labelX),
            y: String(labelY),
            class: `cfg-edge-label cfg-edge-label-${edgeKind}`
        });
        label.textContent = edge.label;
        svg.appendChild(label);
    }
}

function normalizeEdgeKind(label) {
    if (label === 'true' || label === 'false' || label === 'goto') {
        return label;
    }
    return 'next';
}

function createArrowMarkers() {
    const defs = createSvgElement('defs');
    const markers = [
        ['true', '#2f855a'],
        ['false', '#c53030'],
        ['goto', '#b7791f'],
        ['next', '#4a5568']
    ];

    markers.forEach(([kind, color]) => {
        const marker = createSvgElement('marker', {
            id: `arrowhead-${kind}`,
            markerWidth: '10',
            markerHeight: '7',
            refX: '9',
            refY: '3.5',
            orient: 'auto'
        });
        marker.appendChild(createSvgElement('polygon', {
            points: '0 0, 10 3.5, 0 7',
            fill: color
        }));
        defs.appendChild(marker);
    });

    return defs;
}

function drawCfgLegend(svg, width) {
    const items = [
        ['true', 'cfg-edge-true'],
        ['false', 'cfg-edge-false'],
        ['goto', 'cfg-edge-goto'],
        ['next', 'cfg-edge-next']
    ];
    let x = width - 390;

    items.forEach(([label, className]) => {
        const line = createSvgElement('line', {
            x1: String(x),
            y1: '30',
            x2: String(x + 30),
            y2: '30',
            class: `cfg-edge ${className}`
        });
        const text = createSvgElement('text', {
            x: String(x + 38),
            y: '34',
            class: 'cfg-legend-label'
        });
        text.textContent = label;
        svg.appendChild(line);
        svg.appendChild(text);
        x += 90;
    });
}

function createSvgElement(name, attributes = {}) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', name);
    Object.entries(attributes).forEach(([key, value]) => {
        element.setAttribute(key, value);
    });
    return element;
}
