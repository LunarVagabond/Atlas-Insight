import re
from pathlib import Path

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

_SECRET_ENV_RE = re.compile(
    r'^\s*ENV\s+\S*(?:SECRET|KEY|TOKEN|PASSWORD|PASSWD|PWD|API_KEY|PRIVATE)\S*\s*=?\s*\S+',
    re.IGNORECASE,
)
_LATEST_FROM_RE = re.compile(r'^\s*FROM\s+\S+:latest\b', re.IGNORECASE)
_LATEST_FROM_SCRATCH_OK = re.compile(r'^\s*FROM\s+scratch\b', re.IGNORECASE)
_USER_RE = re.compile(r'^\s*USER\s+(\S+)', re.IGNORECASE)
_USER_ROOT_RE = re.compile(r'^\s*USER\s+(?:root|0)\b', re.IGNORECASE)
_ADD_RE = re.compile(r'^\s*ADD\s+(?!https?://)', re.IGNORECASE)
_APT_RE = re.compile(r'apt-get\s+install', re.IGNORECASE)
_APT_CLEAN_RE = re.compile(r'rm\s+-rf\s+/var/lib/apt', re.IGNORECASE)
_APT_RECOMMEND_RE = re.compile(r'--no-install-recommends', re.IGNORECASE)
_FROM_RE = re.compile(r'^\s*FROM\s+', re.IGNORECASE)


def _analyze_dockerfile(path: Path, repo_root: Path) -> dict:
    rel = str(path.relative_to(repo_root))
    issues: list[dict] = []
    has_user = False
    user_is_root = False
    stage_count = 0
    has_apt = False
    has_apt_clean = False
    has_apt_recommend = False

    try:
        lines = path.read_text(errors='ignore').splitlines()
    except OSError:
        return {'path': rel, 'issues': [], 'is_multistage': False, 'runs_as_root': False}

    for lineno, line in enumerate(lines, start=1):
        if _LATEST_FROM_SCRATCH_OK.match(line):
            stage_count += 1
            continue
        if _FROM_RE.match(line):
            stage_count += 1
            if _LATEST_FROM_RE.match(line):
                issues.append({
                    'severity': 'medium',
                    'line': lineno,
                    'message': 'Unpinned base image using :latest tag — builds are not reproducible',  # noqa: E501
                })
        if _SECRET_ENV_RE.match(line):
            issues.append({
                'severity': 'high',
                'line': lineno,
                'message': (
                    'Secret/credential baked into image via ENV'
                    ' — will appear in image layers and history'
                ),
            })
        if _USER_RE.match(line):
            has_user = True
            if _USER_ROOT_RE.match(line):
                user_is_root = True
        if _ADD_RE.match(line):
            issues.append({
                'severity': 'low',
                'line': lineno,
                'message': 'ADD for local files — use COPY (ADD silently extracts tar archives)',
            })
        if _APT_RE.search(line):
            has_apt = True
        if _APT_CLEAN_RE.search(line):
            has_apt_clean = True
        if _APT_RECOMMEND_RE.search(line):
            has_apt_recommend = True

    if not has_user:
        issues.append({
            'severity': 'high',
            'line': None,
            'message': 'No USER directive — container runs as root by default',
        })
        user_is_root = True
    elif user_is_root:
        issues.append({
            'severity': 'high',
            'line': None,
            'message': 'Container explicitly runs as root — use a non-root USER',
        })

    if has_apt and not has_apt_clean:
        issues.append({
            'severity': 'low',
            'line': None,
            'message': 'apt-get install without clearing apt cache — increases image size',
        })
    if has_apt and not has_apt_recommend:
        issues.append({
            'severity': 'low',
            'line': None,
            'message': 'apt-get install without --no-install-recommends — installs extra packages',
        })

    return {
        'path': rel,
        'issues': issues,
        'is_multistage': stage_count > 1,
        'runs_as_root': user_is_root,
    }


def _analyze_compose(path: Path, repo_root: Path) -> dict:
    rel = str(path.relative_to(repo_root))
    issues: list[dict] = []

    if not _HAS_YAML:
        return {'path': rel, 'issues': []}

    try:
        text = path.read_text(errors='ignore')
        data = _yaml.safe_load(text)
    except Exception:
        return {'path': rel, 'issues': []}

    if not isinstance(data, dict):
        return {'path': rel, 'issues': []}

    services = data.get('services', {})
    if not isinstance(services, dict):
        return {'path': rel, 'issues': []}

    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        image = svc.get('image', '')
        if isinstance(image, str) and image.endswith(':latest'):
            issues.append({
                'severity': 'medium',
                'line': None,
                'message': f'Service "{svc_name}": unpinned :latest image tag',
            })
        ports = svc.get('ports', [])
        for port in ports:
            port_str = str(port)
            if port_str.startswith('0.0.0.0:') or re.match(r'^\d+:\d+$', port_str):
                if not svc.get('healthcheck'):
                    issues.append({
                        'severity': 'low',
                        'line': None,
                        'message': f'Service "{svc_name}": port exposed without healthcheck',
                    })
                break

    return {'path': rel, 'issues': issues}


def analyze_containers(repo_dir: str) -> dict:
    root = Path(repo_dir)

    dockerfiles = []
    for p in root.rglob('Dockerfile*'):
        if any(part in {'.git', 'node_modules', 'vendor'} for part in p.parts):
            continue
        if p.is_file():
            dockerfiles.append(_analyze_dockerfile(p, root))

    compose_files = []
    for pattern in ('docker-compose*.yml', 'docker-compose*.yaml', 'compose*.yml', 'compose*.yaml'):
        for p in root.glob(pattern):
            if p.is_file():
                compose_files.append(_analyze_compose(p, root))

    total_issues = (
        sum(len(d['issues']) for d in dockerfiles)
        + sum(len(c['issues']) for c in compose_files)
    )
    high_issues = sum(
        sum(1 for i in d['issues'] if i['severity'] == 'high') for d in dockerfiles
    )
    medium_issues = sum(
        sum(1 for i in d['issues'] if i['severity'] == 'medium')
        for d in dockerfiles + compose_files
    )

    if not dockerfiles and not compose_files:
        score = 0
    else:
        low_issues = total_issues - high_issues - medium_issues
        score = min(100, (high_issues * 25) + (medium_issues * 10) + (low_issues * 3))

    return {
        'dockerfiles': dockerfiles,
        'compose_files': compose_files,
        'dockerfile_count': len(dockerfiles),
        'compose_count': len(compose_files),
        'total_issues': total_issues,
        'score': score,
    }
