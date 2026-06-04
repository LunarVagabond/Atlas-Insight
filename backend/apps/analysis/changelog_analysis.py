import re
from datetime import datetime, timezone
from pathlib import Path

_KEEP_A_CHANGELOG_RE = re.compile(
    r'##\s+\[(?:unreleased|\d+\.\d+(?:\.\d+)?(?:-[^\]]+)?)\]',
    re.IGNORECASE,
)
_VERSIONED_RE = re.compile(
    r'(?:^|\n)##\s+v?\d+\.\d+',
    re.MULTILINE | re.IGNORECASE,
)
_DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
_VERSION_IN_HEADING_RE = re.compile(
    r'##\s+(?:\[?)v?(\d+\.\d+(?:\.\d+)?(?:[-.\w]+)?)(?:\]?)',
    re.IGNORECASE,
)
_MAX_READ_BYTES = 20480
_STALE_THRESHOLD_DAYS = 90


def analyze_changelog(repo_dir: str, structure: dict, commits: dict) -> dict:
    found = structure.get('has_changelog', False)
    changelog_file = structure.get('changelog_file')
    issues: list[dict] = []

    if not found or not changelog_file:
        issues.append({
            'severity': 'low',
            'message': (
                'No CHANGELOG file found — contributors might have trouble tracking'
                ' what changed between versions'
            ),
        })
        return {
            'found': False,
            'filename': None,
            'format': 'none',
            'entry_count': 0,
            'last_entry_date': None,
            'last_entry_version': None,
            'days_stale': None,
            'issues': issues,
        }

    changelog_path = Path(repo_dir) / changelog_file
    try:
        text = changelog_path.read_text(errors='ignore')[:_MAX_READ_BYTES]
    except OSError:
        return {
            'found': True,
            'filename': changelog_file,
            'format': 'none',
            'entry_count': 0,
            'last_entry_date': None,
            'last_entry_version': None,
            'days_stale': None,
            'issues': [{'severity': 'low', 'message': 'CHANGELOG file exists but could not be read'}],  # noqa: E501
        }

    if _KEEP_A_CHANGELOG_RE.search(text):
        fmt = 'keep-a-changelog'
        entry_count = len(_KEEP_A_CHANGELOG_RE.findall(text))
    elif _VERSIONED_RE.search(text):
        fmt = 'versioned'
        entry_count = len(_VERSIONED_RE.findall(text))
    else:
        fmt = 'prose'
        entry_count = 1

    dates = _DATE_RE.findall(text)
    last_entry_date: str | None = None
    days_stale: int | None = None

    if dates:
        last_entry_date = dates[0]
        try:
            entry_dt = datetime.strptime(last_entry_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            days_stale = (datetime.now(timezone.utc) - entry_dt).days
        except ValueError:
            pass

    version_matches = _VERSION_IN_HEADING_RE.findall(text)
    last_entry_version = version_matches[0] if version_matches else None

    if fmt == 'prose':
        issues.append({
            'severity': 'low',
            'message': (
                'CHANGELOG has no versioned entries'
                ' — consider Keep a Changelog format (keepachangelog.com)'
            ),
        })

    if entry_count == 0:
        issues.append({
            'severity': 'low',
            'message': 'CHANGELOG has no version entries',
        })

    last_commit_date_str = commits.get('last_commit_date')
    if days_stale is not None and last_commit_date_str:
        try:
            if isinstance(last_commit_date_str, str):
                commit_dt = datetime.fromisoformat(last_commit_date_str.replace('Z', '+00:00'))
            else:
                commit_dt = last_commit_date_str
                if commit_dt.tzinfo is None:
                    commit_dt = commit_dt.replace(tzinfo=timezone.utc)
            repo_active = commits.get('days_since_last_commit', 9999) < 365
            if days_stale > _STALE_THRESHOLD_DAYS and repo_active:
                issues.append({
                    'severity': 'medium',
                    'message': (
                        f'CHANGELOG last updated {days_stale} days ago'
                        ' but repo is actively maintained'
                    ),
                })
        except Exception:
            pass

    return {
        'found': True,
        'filename': changelog_file,
        'format': fmt,
        'entry_count': entry_count,
        'last_entry_date': last_entry_date,
        'last_entry_version': last_entry_version,
        'days_stale': days_stale,
        'issues': issues,
    }
