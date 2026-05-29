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


def scan_security(repo_obj: Repo, repo_dir: str) -> dict:
    base = Path(repo_dir)
    issues = []

    # Check for sensitive files tracked in git
    try:
        tracked = repo_obj.git.ls_files().splitlines()
        seen: set[str] = set()
        for tracked_file in tracked:
            tf_lower = tracked_file.lower()
            if SAFE_PATTERNS.search(tf_lower):
                continue
            for pattern, severity, label in SENSITIVE_GIT_PATTERNS:
                if re.search(pattern, tf_lower, re.IGNORECASE) and label not in seen:
                    issues.append({
                        'severity': severity,
                        'type': 'sensitive_file_committed',
                        'detail': f'{label}: {tracked_file}',
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
            gi_content = gitignore_path.read_text(errors='ignore').lower()
            for pattern in GITIGNORE_RECOMMENDED:
                if pattern.lower() not in gi_content:
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
