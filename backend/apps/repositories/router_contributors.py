"""Contributors endpoint — reads contributors/ directory and cross-references git history."""
import json
import re
import subprocess
from pathlib import Path

from django.conf import settings
from ninja import Router

router = Router(tags=['contributors'])

_CONTRIBUTORS_DIR = Path(settings.BASE_DIR) / 'contributors'
_STATS_CACHE = Path(settings.BASE_DIR) / 'contributors_stats.json'

BIO_MAX_CHARS = 500

_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
_FM_FIELD_RE = re.compile(r'^(\w+):\s*(.+)$', re.MULTILINE)


def _parse_md_file(text: str) -> tuple[dict[str, str], str]:
    """Returns (frontmatter_fields, body_without_frontmatter)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields = dict(_FM_FIELD_RE.findall(m.group(1)))
    body = text[m.end():].strip()
    return fields, body


def _emails_from_frontmatter(fm: dict[str, str]) -> list[str]:
    """Parse git_emails (comma-sep) or legacy git_email field."""
    raw = fm.get('git_emails') or fm.get('git_email') or ''
    return [e.strip().lower() for e in raw.split(',') if e.strip()]


def _parse_git_log() -> dict[str, dict]:
    """
    Returns dict mapping lowercase author email → stats.
    Reads from pre-built cache if available (Docker / CI builds).
    """
    if _STATS_CACHE.exists():
        try:
            return json.loads(_STATS_CACHE.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    try:
        out = subprocess.check_output(
            ['git', 'log', '--numstat', '--no-merges', '--format=COMMIT\t%ae\t%an'],
            cwd=str(settings.REPO_ROOT),
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    authors: dict[str, dict] = {}
    current_email = ''
    current_name = ''

    for line in out.splitlines():
        if line.startswith('COMMIT\t'):
            parts = line.split('\t', 2)
            current_email = parts[1].lower() if len(parts) > 1 else ''
            current_name = parts[2] if len(parts) > 2 else ''
            if current_email and current_email not in authors:
                authors[current_email] = {
                    'name': current_name,
                    'email': current_email,
                    'lines_added': 0,
                    'lines_removed': 0,
                    'commit_count': 0,
                    'contrib_only_lines': 0,
                }
            if current_email:
                authors[current_email]['commit_count'] += 1
        elif line and current_email:
            parts = line.split('\t')
            if len(parts) == 3:
                try:
                    added = int(parts[0])
                    removed = int(parts[1])
                except ValueError:
                    continue
                file_path = parts[2]
                authors[current_email]['lines_added'] += added
                authors[current_email]['lines_removed'] += removed
                if file_path.startswith('contributors/'):
                    authors[current_email]['contrib_only_lines'] += added

    return authors


def _merge_author_stats(emails: list[str], authors: dict[str, dict]) -> dict | None:
    """Merge stats across all matching email identities for one contributor."""
    matched = [authors[e] for e in emails if e in authors]
    if not matched:
        return None
    merged = {
        'name': matched[0]['name'],
        'email': matched[0]['email'],
        'lines_added': sum(a['lines_added'] for a in matched),
        'lines_removed': sum(a['lines_removed'] for a in matched),
        'commit_count': sum(a['commit_count'] for a in matched),
        'contrib_only_lines': sum(a['contrib_only_lines'] for a in matched),
    }
    return merged


def _has_non_contrib_locs(author_data: dict) -> bool:
    non_contrib = author_data['lines_added'] - author_data['contrib_only_lines']
    return non_contrib > 0


def _truncate_bio(bio_md: str) -> str:
    if len(bio_md) <= BIO_MAX_CHARS:
        return bio_md
    truncated = bio_md[:BIO_MAX_CHARS]
    # don't cut mid-word
    last_space = truncated.rfind(' ')
    if last_space > BIO_MAX_CHARS // 2:
        truncated = truncated[:last_space]
    return truncated + '…'


@router.get('/contributors/')
def list_contributors(request, page: int = 1, per_page: int = 20, q: str = ''):
    if per_page > 50:
        per_page = 50

    if not _CONTRIBUTORS_DIR.exists():
        return {'items': [], 'total': 0, 'page': page, 'per_page': per_page}

    authors = _parse_git_log()

    items = []
    for md_file in sorted(_CONTRIBUTORS_DIR.glob('*.md')):
        username = md_file.stem
        raw = md_file.read_text(encoding='utf-8').strip()
        frontmatter, bio_md = _parse_md_file(raw)

        emails = _emails_from_frontmatter(frontmatter)
        author_data = _merge_author_stats(emails, authors) if emails else None

        # Fallback: substring match on username vs name/email
        if author_data is None:
            username_lower = username.lower()
            for data in authors.values():
                if (
                    username_lower in data['name'].lower()
                    or username_lower in data['email'].lower()
                ):
                    author_data = data
                    break

        if author_data is None or not _has_non_contrib_locs(author_data):
            continue

        bio_md = _truncate_bio(bio_md)

        if q:
            q_lower = q.lower()
            if q_lower not in username.lower() and q_lower not in bio_md.lower():
                continue

        items.append({
            'username': username,
            'bio_md': bio_md,
            'lines_added': author_data['lines_added'] - author_data['contrib_only_lines'],
            'lines_removed': author_data['lines_removed'],
            'commit_count': author_data['commit_count'],
        })

    total = len(items)
    offset = (page - 1) * per_page
    return {
        'items': items[offset:offset + per_page],
        'total': total,
        'page': page,
        'per_page': per_page,
    }
