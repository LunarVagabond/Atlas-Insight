import re
from pathlib import Path

from git import Repo

SENSITIVE_GIT_PATTERNS = [
    (r'(^|/)\.env$', 'high', '.env file committed'),
    (r'(^|/)\.env\.[^e][^x]', 'high', '.env variant committed'),
    (r'\.(pem|key|p12|pfx|crt|cer)$', 'high', 'Certificate/key file committed'),
    (r'(^|/)id_(rsa|dsa|ecdsa|ed25519)$', 'high', 'SSH private key committed'),
    (r'credentials\.json$', 'high', 'credentials.json committed'),
    (r'service.?account\.json$', 'high', 'Service account key committed'),
    (r'(^|/)secrets?\.(json|yaml|yml)$', 'medium', 'Secrets file committed'),
    (r'\.p8$', 'medium', 'Apple private key committed'),
    (r'(^|/)\.htpasswd$', 'medium', '.htpasswd committed'),
]

SAFE_PATTERNS = re.compile(
    r'\.(example|sample|template|test|dist|stub|fake)$', re.IGNORECASE
)

GITIGNORE_RECOMMENDED = [
    '.env', '*.pem', '*.key', 'id_rsa', 'node_modules',
    '__pycache__', '.venv', 'venv', '*.log', 'dist/',
]


def _gitignore_covers(pattern: str, gi_lines_lower: list[str]) -> bool:
    """Return True if any non-comment gitignore line covers this pattern."""
    for line in gi_lines_lower:
        if line == pattern:
            return True
        if line == f'/{pattern}':
            return True
        # *.ext pattern: a line like "*.log" covers "*.log"; also "**/*.log" covers it
        if pattern.startswith('*.') and line.endswith(pattern[1:]):
            return True
        # plain name (no glob, no dot prefix): exact word match only, not substring
        if '*' not in pattern and not pattern.startswith('.'):
            if line == pattern or line == f'/{pattern}' or line == f'{pattern}/':
                return True
        # dot-prefix pattern like ".env": covered by ".env" or ".env*" lines
        if pattern.startswith('.') and (line == pattern or line.startswith(f'{pattern}.')):
            return True
    return False


def scan_security(repo_obj: Repo, repo_dir: str, path_prefix: str | None = None) -> dict:
    base = Path(repo_dir)
    issues = []

    # Check for sensitive files tracked in git
    try:
        tracked = repo_obj.git.ls_files().splitlines()
        if path_prefix:
            tracked = [f for f in tracked if f.startswith(path_prefix)]
        seen: set[str] = set()
        for tracked_file in tracked:
            tf_lower = tracked_file.lower()
            if SAFE_PATTERNS.search(tf_lower):
                continue
            for pattern, severity, label in SENSITIVE_GIT_PATTERNS:
                if re.search(pattern, tf_lower, re.IGNORECASE) and label not in seen:
                    commit_sha = None
                    commit_author = None
                    try:
                        log_line = repo_obj.git.log(
                            '-1', '--pretty=format:%h|||%an', '--', tracked_file
                        )
                        if log_line and '|||' in log_line:
                            sha_part, author_part = log_line.split('|||', 1)
                            commit_sha = sha_part.strip() or None
                            commit_author = author_part.strip() or None
                    except Exception:
                        pass
                    issues.append({
                        'severity': severity,
                        'type': 'sensitive_file_committed',
                        'detail': f'{label}: {tracked_file}',
                        'commit_sha': commit_sha,
                        'commit_author': commit_author,
                    })
                    seen.add(label)
                    break
    except Exception:
        pass

    # .gitignore quality
    gitignore_path = base / '.gitignore'
    gitignore_missing = not gitignore_path.exists()
    gitignore_gaps: list[str] = []

    if gitignore_path.exists():
        try:
            gi_raw = gitignore_path.read_text(errors='ignore')
            gi_lines = [
                line.strip().rstrip('/')
                for line in gi_raw.splitlines()
                if line.strip() and not line.strip().startswith('#')
            ]
            gi_lines_lower = [l.lower() for l in gi_lines]
            for pattern in GITIGNORE_RECOMMENDED:
                pat = pattern.lower().rstrip('/')
                if not _gitignore_covers(pat, gi_lines_lower):
                    gitignore_gaps.append(pattern)
        except Exception:
            pass

    if gitignore_missing:
        issues.append(
            {'severity': 'medium', 'type': 'no_gitignore', 'detail': '.gitignore missing'}
        )
    elif gitignore_gaps:
        issues.append({
            'severity': 'low',
            'type': 'gitignore_gaps',
            'detail': f'.gitignore missing recommended patterns: {", ".join(gitignore_gaps[:5])}',
        })

    severity_weights = {'high': 35, 'medium': 15, 'low': 5}
    score = min(100, sum(severity_weights.get(i['severity'], 5) for i in issues))

    return {
        'issues': issues,
        'issue_count': len(issues),
        'score': score,
        'gitignore_exists': not gitignore_missing,
        'gitignore_gaps': gitignore_gaps,
    }
