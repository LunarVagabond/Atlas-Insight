def compute_run_diff(curr: dict, prev: dict, prev_run_id, prev_triggered_at) -> dict:
    curr_h = {h['signal']: h for h in curr.get('heuristics', [])}
    prev_h = {h['signal']: h for h in prev.get('heuristics', [])}
    heuristic_deltas = []
    for signal, ch in curr_h.items():
        ph = prev_h.get(signal)
        if ph:
            delta = ch['score'] - ph['score']
            heuristic_deltas.append({
                'signal': signal,
                'label': ch['label'],
                'before': ph['score'],
                'after': ch['score'],
                'delta': delta,
                'direction': 'up' if delta > 2 else 'down' if delta < -2 else 'same',
            })

    curr_dep_names = {d['name'] for d in curr.get('dependencies', {}).get('dependencies', [])}
    prev_dep_names = {d['name'] for d in prev.get('dependencies', {}).get('dependencies', [])}

    curr_struct = curr.get('structure', {})
    prev_struct = prev.get('structure', {})
    curr_graph = curr.get('graph', {})
    prev_graph = prev.get('graph', {})
    curr_cls = curr.get('classification', {})
    prev_cls = prev.get('classification', {})

    def cls_delta(key):
        c = curr_cls.get(key, {})
        p = prev_cls.get(key, {})
        if not c or not p:
            return None
        return {
            'before_label': p.get('label'),
            'after_label': c.get('label'),
            'delta': c.get('score', 0) - p.get('score', 0),
            'changed': c.get('key') != p.get('key'),
        }

    return {
        'available': True,
        'previous_run_id': str(prev_run_id),
        'previous_triggered_at': prev_triggered_at.isoformat(),
        'heuristics': heuristic_deltas,
        'dependencies': {
            'added': sorted(curr_dep_names - prev_dep_names)[:20],
            'removed': sorted(prev_dep_names - curr_dep_names)[:20],
            'added_count': len(curr_dep_names - prev_dep_names),
            'removed_count': len(prev_dep_names - curr_dep_names),
        },
        'contributors': {
            'before': prev.get('commits', {}).get('total_contributors', 0),
            'after': curr.get('commits', {}).get('total_contributors', 0),
            'delta': curr.get('commits', {}).get('total_contributors', 0) - prev.get('commits', {}).get('total_contributors', 0),
        },
        'graph': {
            'nodes_before': prev_graph.get('node_count', 0),
            'nodes_after': curr_graph.get('node_count', 0),
            'nodes_delta': curr_graph.get('node_count', 0) - prev_graph.get('node_count', 0),
            'god_modules_before': len(prev_graph.get('god_modules', [])),
            'god_modules_after': len(curr_graph.get('god_modules', [])),
            'god_modules_delta': len(curr_graph.get('god_modules', [])) - len(prev_graph.get('god_modules', [])),
        },
        'structure': {
            'files_before': prev_struct.get('total_files', 0),
            'files_after': curr_struct.get('total_files', 0),
            'files_delta': curr_struct.get('total_files', 0) - prev_struct.get('total_files', 0),
            'test_ratio_before': round(prev_struct.get('test_ratio', 0), 3),
            'test_ratio_after': round(curr_struct.get('test_ratio', 0), 3),
        },
        'classification': {
            'project_health': cls_delta('project_health'),
            'contribution_difficulty': cls_delta('contribution_difficulty'),
            'documentation_grade': cls_delta('documentation_grade'),
            'code_complexity': cls_delta('code_complexity'),
        },
    }
