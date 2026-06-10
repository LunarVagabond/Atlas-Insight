from __future__ import annotations

import re

_MONTH_MAP: dict[str, int] = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 7, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

_LIST_RE = re.compile(r'^\s*(?:[-+*]|\d+\.)\s+(.+)$')
_STRUCK_RE = re.compile(r'^~~(.+)~~$')
_DONE_BOX_RE = re.compile(r'^\[([xX])\]\s*(.+)$')
_TODO_BOX_RE = re.compile(r'^\[\s\]\s*(.+)$')
_DONE_PREFIX_RE = re.compile(
    r'^(?:'
    r'(?:✅|☑️|☑|✓|✔)\s*'
    r'|\*\*(?:done|completed|shipped|finished):\*\*\s*'
    r'|\*\*(?:done|completed|shipped|finished)\*\*\s*:\s*'
    r'|(?:done|completed|shipped|finished)\s*:\s*'
    r')',
    re.I,
)
_DONE_SUFFIX_RE = re.compile(
    r'\s*(?:\(done\)|\[done\]|\(completed\)|\[completed\]|✅|✓)\s*$',
    re.I,
)
_INLINE_STRUCK_RE = re.compile(r'~~(.+?)~~')
_SUBSECTION_RE = re.compile(r'^\s*\*\*([^*]+)\*\*\s*$')
_SUBSECTION_DONE_RE = re.compile(
    r'^(?:done|completed|shipped|finished|released)(?:\s|$)',
    re.I,
)
_INFO_TITLE_RE = re.compile(
    r'(?:^|\b)(?:'
    r'how to (?:read|use)|about (?:this|the)|legend|introduction|intro|overview|'
    r'working notes?|background|glossary|conventions?|reading guide|'
    r'what(?:\'s| is) (?:new|next)|changelog'
    r')(?:\b|$)',
    re.I,
)
_SKIP_LINE_RE = re.compile(r'^\s*(?:---+|\*\*\*+|___+)\s*$')
_BLOCKQUOTE_RE = re.compile(r'^\s*>\s*(.*)$')


def _extract_date(text: str) -> str | None:
    m = re.search(r'\b(\d{4})[-\s]Q([1-4])\b|\bQ([1-4])[\s/]+(\d{4})\b', text, re.I)
    if m:
        year = int(m.group(1) or m.group(4))
        q = int(m.group(2) or m.group(3))
        return f'{year}-Q{q}'

    month_re = '|'.join(_MONTH_MAP.keys())
    m = re.search(rf'\b({month_re})\.?\s+(\d{{4}})\b', text, re.I)
    if m:
        month = _MONTH_MAP[m.group(1).lower()]
        return f'{m.group(2)}-{month:02d}'

    m = re.search(r'\b(20\d{2})-(0[1-9]|1[0-2])\b', text)
    if m:
        return f'{m.group(1)}-{m.group(2)}'

    m = re.search(r'\b(20[2-9]\d)\b', text)
    if m:
        return m.group(1)

    return None


def _clean_text(text: str) -> str:
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[`*_]{1,2}([^`*_]+)[`*_]{1,2}', r'\1', text)
    text = _INLINE_STRUCK_RE.sub(r'\1', text)
    return text.strip()


def _is_informational_title(title: str) -> bool:
    return bool(_INFO_TITLE_RE.search(title))


def _classify_item(raw: str, *, context_done: bool = False) -> tuple[str, str] | None:
    lm = _LIST_RE.match(raw)
    if not lm:
        return None
    content = lm.group(1).strip()

    dm = _DONE_BOX_RE.match(content)
    if dm:
        return ('done', dm.group(2).strip())
    tm = _TODO_BOX_RE.match(content)
    if tm:
        return ('todo', tm.group(1).strip())

    sm = _STRUCK_RE.match(content)
    if sm:
        return ('done', sm.group(1).strip())

    prefix = _DONE_PREFIX_RE.match(content)
    if prefix:
        rest = content[prefix.end():].strip()
        if rest:
            return ('done', rest)

    suffix = _DONE_SUFFIX_RE.search(content)
    if suffix:
        head = content[:suffix.start()].strip()
        if head:
            return ('done', head)

    if _INLINE_STRUCK_RE.search(content):
        return ('done', _INLINE_STRUCK_RE.sub(r'\1', content).strip())

    if context_done:
        return ('done', content)

    return ('todo', content)


def _line_as_note(raw: str) -> str | None:
    stripped = raw.strip()
    if not stripped or _SKIP_LINE_RE.match(stripped):
        return None
    bq = _BLOCKQUOTE_RE.match(stripped)
    if bq:
        text = bq.group(1).strip()
        return _clean_text(text) if text else None
    if _LIST_RE.match(raw) or _SUBSECTION_RE.match(stripped):
        return None
    if stripped.startswith('#'):
        return None
    return _clean_text(stripped)


def _finalize(title: str, lines: list[str]) -> dict:
    body = '\n'.join(lines)
    date = _extract_date(title) or _extract_date(body[:400])
    informational = _is_informational_title(title)

    done: list[str] = []
    todo: list[str] = []
    notes: list[str] = []
    context_done = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        sub = _SUBSECTION_RE.match(stripped)
        if sub:
            sub_title = sub.group(1).strip()
            context_done = bool(_SUBSECTION_DONE_RE.match(sub_title))
            continue

        result = _classify_item(line, context_done=context_done)
        if result:
            status, text = result
            text = _clean_text(text)
            if not text:
                continue
            if informational:
                notes.append(text)
            elif status == 'done':
                done.append(text)
            else:
                todo.append(text)
            continue

        note = _line_as_note(line)
        if note:
            notes.append(note)

    kind = 'informational' if informational else 'milestone'

    if kind == 'informational':
        done = []
        todo = []

    if done and not todo:
        status_val = 'done'
    elif done:
        status_val = 'in-progress'
    elif kind == 'informational':
        status_val = 'informational'
    else:
        status_val = 'planned'

    return {
        'title': title,
        'date': date,
        'kind': kind,
        'status': status_val,
        'done_count': len(done),
        'todo_count': len(todo),
        'done_items': done[:6],
        'todo_items': todo[:6],
        'notes': notes[:6],
    }


def _section_has_content(section: dict) -> bool:
    if section['kind'] == 'informational':
        return bool(section['notes'] or section['date'])
    return bool(section['done_count'] or section['todo_count'] or section['date'])


def parse_roadmap(content: str) -> dict:
    milestones: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in content.split('\n'):
        hm = re.match(r'^#{1,4}\s+(.+)$', line)
        if hm:
            if current_title is not None:
                m = _finalize(current_title, current_lines)
                if _section_has_content(m):
                    milestones.append(m)
            current_title = hm.group(1).strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        m = _finalize(current_title, current_lines)
        if _section_has_content(m):
            milestones.append(m)

    return {'milestones': milestones[:24]}
