from __future__ import annotations
import collections

_TODO_PRIORITY = {'BUG': 0, 'FIXME': 1, 'HACK': 2, 'XXX': 3, 'TODO': 4, 'OPTIMIZE': 5}
_TODO_DIFFICULTY = {
    'BUG': 'beginner', 'FIXME': 'beginner', 'HACK': 'intermediate',
    'XXX': 'intermediate', 'TODO': 'beginner', 'OPTIMIZE': 'beginner',
}
_TODO_RISK = {
    'BUG': 'medium', 'FIXME': 'medium', 'HACK': 'medium',
    'XXX': 'medium', 'TODO': 'low', 'OPTIMIZE': 'low',
}


def generate_todo_opportunities(todos: dict) -> list[dict]:
    items = todos.get('items', [])
    sorted_items = sorted(
        items,
        key=lambda m: (_TODO_PRIORITY.get(m['type'].upper(), 9), m['file'], m['line']),
    )
    opps = []
    for m in sorted_items[:20]:
        mtype = m['type'].upper()
        basename = m['file'].split('/')[-1]
        text = m['text'].strip() if m['text'] else ''
        title = f'{mtype}: {text[:60]}' if text else f'Resolve {mtype} in {basename}'
        desc = (
            f'`{m["file"]}` line {m["line"]} contains a {mtype} marker'
            + (f': "{text}"' if text else '') + '.'
        )
        opps.append({
            'id': f'todo_{mtype}_{basename}_{m["line"]}',
            'title': title,
            'description': desc,
            'difficulty': _TODO_DIFFICULTY.get(mtype, 'beginner'),
            'risk': _TODO_RISK.get(mtype, 'low'),
            'category': 'refactoring',
            'hints': [
                f'Open `{m["file"]}` at line {m["line"]}',
                'Read the surrounding context to understand what was left unfinished',
                'Fix, remove, or convert to a tracked issue if out of scope for a quick PR',
            ],
        })
    return opps


def generate_revert_opportunities(commits: dict) -> list[dict]:
    file_revert_count: dict[str, int] = collections.defaultdict(int)
    for rc in commits.get('reverted_commits', []):
        for f in rc.get('files', []):
            file_revert_count[f] += 1

    opps = []
    for file, count in sorted(file_revert_count.items(), key=lambda kv: -kv[1]):
        if count < 3:
            continue
        basename = file.split('/')[-1]
        opps.append({
            'id': f'revert_hotspot_{basename}',
            'title': f'Investigate historically problematic area: {basename}',
            'description': f'{file} has been part of {count} reverted commits, suggesting recurring instability or unclear requirements.',
            'difficulty': 'intermediate',
            'risk': 'medium',
            'category': 'refactoring',
            'hints': [
                f'Open `{file}` and read through its git history: `git log --follow -p {file}`',
                'Look for recurring patterns in the reverted changes — they often reveal a missing abstraction or unclear ownership',
                'Consider adding tests before making changes to catch regressions early',
            ],
        })
        if len(opps) >= 5:
            break
    return opps
