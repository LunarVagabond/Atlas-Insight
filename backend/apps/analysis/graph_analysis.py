import networkx as nx

GOD_MODULE_THRESHOLD = 10


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
        if deg >= GOD_MODULE_THRESHOLD
    ][:20]

    # Hotspots: top 20 by combined in+out degree
    hotspots = sorted(
        [{'file': n, 'degree': graph.degree(n)} for n in graph.nodes()],
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
