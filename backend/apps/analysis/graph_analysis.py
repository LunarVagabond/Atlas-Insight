from pathlib import Path

import networkx as nx

from .project_structure import FRAMEWORK_PACKAGES

GOD_MODULE_THRESHOLD = 10


def _is_framework_node(node: str) -> bool:
    """Return True if node is a known framework package (not an internal file)."""
    # Bare name check: 'vue', 'react', 'django'
    if node in FRAMEWORK_PACKAGES:
        return True
    # Stem check: covers paths like 'node_modules/vue' or just the basename
    stem = Path(node).stem.lower()
    if stem in FRAMEWORK_PACKAGES:
        return True
    return False


def analyze_graph(edges: list[dict]) -> dict:
    graph = nx.DiGraph()
    for e in edges:
        graph.add_edge(e['source'], e['target'])

    # Compute cycles once
    try:
        all_cycles = list(nx.simple_cycles(graph))
    except Exception:
        all_cycles = []

    in_degrees = dict(graph.in_degree())
    god_modules = [
        {'module': node, 'in_degree': deg}
        for node, deg in sorted(in_degrees.items(), key=lambda x: -x[1])
        if deg >= GOD_MODULE_THRESHOLD and not _is_framework_node(node)
    ][:20]

    # Hotspots: top 20 by combined in+out degree, excluding god modules
    god_module_set = {m['module'] for m in god_modules}
    hotspots = sorted(
        [
            {'file': n, 'degree': graph.degree(n)}
            for n in graph.nodes()
            if n not in god_module_set
        ],
        key=lambda x: -x['degree'],
    )[:20]

    return {
        'node_count': graph.number_of_nodes(),
        'edge_count': graph.number_of_edges(),
        'cycles': all_cycles[:20],
        'cycle_count': len(all_cycles),
        'god_modules': god_modules,
        'hotspots': hotspots,
        'nodes': [
            {'id': n, 'in_degree': in_degrees.get(n, 0)} for n in list(graph.nodes())[:500]
        ],
        'edges': [{'source': u, 'target': v} for u, v in list(graph.edges())[:1000]],
    }
