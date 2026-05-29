from __future__ import annotations

import re

_MONTH_MAP: dict[str, int] = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

# Matches any list item prefix: "- ", "+ ", "* ", "1. ", "2. " …
_LIST_RE = re.compile(r'^\s*(?:[-+*]|\d+\.)\s+(.+)$')
# Fully struck-through: ~~text~~ covering the whole content
_STRUCK_RE = re.compile(r'^~~(.+)~~$')
# Checkbox done: [x] / [X]
_DONE_BOX_RE = re.compile(r'^\[([xX])\]\s*(.+)$')
# Checkbox todo: [ ]
_TODO_BOX_RE = re.compile(r'^\[\s\]\s*(.+)$')


def _extract_date(text: str) -> str | None:
    # 2025-Q1 or Q1 2025 or Q1/2025
    m = re.search(r'\b(\d{4})[-\s]Q([1-4])\b|\bQ([1-4])[\s/]+(\d{4})\b', text, re.I)
    if m:
        year = int(m.group(1) or m.group(4))
        q = int(m.group(2) or m.group(3))
        return f'{year}-Q{q}'

    # Month Year
    month_re = '|'.join(_MONTH_MAP.keys())
    m = re.search(rf'\b({month_re})\.?\s+(\d{{4}})\b', text, re.I)
    if m:
        month = _MONTH_MAP[m.group(1).lower()]
        return f'{m.group(2)}-{month:02d}'

    # YYYY-MM
    m = re.search(r'\b(20\d{2})-(0[1-9]|1[0-2])\b', text)
    if m:
        return f'{m.group(1)}-{m.group(2)}'

    # Bare year
    m = re.search(r'\b(20[2-9]\d)\b', text)
    if m:
        return m.group(1)

    return None


def _classify_item(raw: str) -> tuple[str, str] | None:
    """Return (status, text) for a list item line, or None if not a list item."""
    lm = _LIST_RE.match(raw)
    if not lm:
        return None
    content = lm.group(1).strip()

    # Checkbox patterns take priority
    dm = _DONE_BOX_RE.match(content)
    if dm:
        return ('done', dm.group(2).strip())
    tm = _TODO_BOX_RE.match(content)
    if tm:
        return ('todo', tm.group(1).strip())

    # Strikethrough = done
    sm = _STRUCK_RE.match(content)
    if sm:
        return ('done', sm.group(1).strip())

    # Plain list item = todo
    return ('todo', content)


def _finalize(title: str, lines: list[str]) -> dict:
    body = '\n'.join(lines)
    date = _extract_date(title) or _extract_date(body[:400])

    done: list[str] = []
    todo: list[str] = []

    for line in lines:
        result = _classify_item(line)
        if result:
            status, text = result
            # Strip any remaining markdown (inline code, links, bold)
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # links
            text = re.sub(r'[`*_]{1,2}([^`*_]+)[`*_]{1,2}', r'\1', text)  # inline formatting
            text = text.strip()
            if text:
                if status == 'done':
                    done.append(text)
                else:
                    todo.append(text)

    if done and not todo:
        status_val = 'done'
    elif done:
        status_val = 'in-progress'
    else:
        status_val = 'planned'

    return {
        'title': title,
        'date': date,
        'status': status_val,
        'done_count': len(done),
        'todo_count': len(todo),
        'done_items': done[:6],
        'todo_items': todo[:6],
    }


def parse_roadmap(content: str) -> dict:
    milestones: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in content.split('\n'):
        hm = re.match(r'^#{1,4}\s+(.+)$', line)
        if hm:
            if current_title is not None:
                m = _finalize(current_title, current_lines)
                # Include if it has any items OR a date — drop empty boilerplate sections
                if m['done_count'] or m['todo_count'] or m['date']:
                    milestones.append(m)
            current_title = hm.group(1).strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        m = _finalize(current_title, current_lines)
        if m['done_count'] or m['todo_count'] or m['date']:
            milestones.append(m)

    return {'milestones': milestones[:24]}
