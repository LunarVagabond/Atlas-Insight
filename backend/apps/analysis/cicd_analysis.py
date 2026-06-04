import re
from pathlib import Path

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

_TEST_KEYWORDS = re.compile(
    r'\b(pytest|jest|vitest|mocha|rspec|minitest|phpunit|unittest|cargo\s+test|go\s+test|'
    r'mvn\s+test|gradle\s+test|dotnet\s+test|xunit|nunit|run\s+tests?)\b',
    re.IGNORECASE,
)
_LINT_KEYWORDS = re.compile(
    r'\b(ruff|eslint|pylint|flake8|black|rubocop|golint|golangci|mypy|pyright|'
    r'tsc\s+--|vue-tsc|biome|shellcheck|hadolint|markdownlint)\b',
    re.IGNORECASE,
)
_DEPLOY_KEYWORDS = re.compile(
    r'\b(deploy|publish|release|helm\s+upgrade|kubectl\s+apply|'
    r'heroku|vercel|netlify|fly\.io|railway|render|eb\s+deploy)\b',
    re.IGNORECASE,
)
_CONTAINER_KEYWORDS = re.compile(
    r'\b(docker\s+build|docker\s+push|buildx|kaniko|podman\s+build)\b',
    re.IGNORECASE,
)

_GH_WORKFLOWS_DIR = '.github/workflows'


def _flatten_text(obj, _depth=0) -> str:
    if _depth > 8:
        return ''
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return ' '.join(_flatten_text(i, _depth + 1) for i in obj)
    if isinstance(obj, dict):
        return ' '.join(_flatten_text(v, _depth + 1) for v in obj.values())
    return str(obj) if obj is not None else ''


def _parse_github_workflow(path: Path) -> dict | None:
    if not _HAS_YAML:
        return None
    try:
        data = _yaml.safe_load(path.read_text(errors='ignore'))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    name = data.get('name') or path.stem

    on_value = data.get('on') or data.get(True) or {}
    if isinstance(on_value, str):
        triggers = [on_value]
    elif isinstance(on_value, list):
        triggers = [str(t) for t in on_value]
    elif isinstance(on_value, dict):
        triggers = list(on_value.keys())
    else:
        triggers = []

    jobs = data.get('jobs', {})
    job_count = len(jobs) if isinstance(jobs, dict) else 0

    full_text = _flatten_text(jobs)

    uses_matrix = 'matrix' in full_text.lower()

    return {
        'name': name,
        'triggers': triggers,
        'has_tests': bool(_TEST_KEYWORDS.search(full_text)),
        'has_lint': bool(_LINT_KEYWORDS.search(full_text)),
        'has_deploy': bool(_DEPLOY_KEYWORDS.search(full_text)),
        'has_container_build': bool(_CONTAINER_KEYWORDS.search(full_text)),
        'job_count': job_count,
        'uses_matrix': uses_matrix,
    }


def _parse_generic_ci(path: Path) -> dict | None:
    try:
        text = path.read_text(errors='ignore')[:16384]
    except OSError:
        return None

    return {
        'name': path.name,
        'triggers': [],
        'has_tests': bool(_TEST_KEYWORDS.search(text)),
        'has_lint': bool(_LINT_KEYWORDS.search(text)),
        'has_deploy': bool(_DEPLOY_KEYWORDS.search(text)),
        'has_container_build': bool(_CONTAINER_KEYWORDS.search(text)),
        'job_count': 0,
        'uses_matrix': 'matrix' in text.lower(),
    }


def analyze_cicd(repo_dir: str, structure: dict) -> dict:
    root = Path(repo_dir)
    workflows: list[dict] = []
    system: str | None = None

    gh_workflows_path = root / _GH_WORKFLOWS_DIR
    if gh_workflows_path.is_dir():
        system = 'github_actions'
        yml_files = (
            sorted(gh_workflows_path.glob('*.yml'))
            + sorted(gh_workflows_path.glob('*.yaml'))
        )
        for wf_file in yml_files:
            parsed = _parse_github_workflow(wf_file)
            if parsed:
                workflows.append(parsed)

    if not workflows:
        other_ci_files = [
            ('.travis.yml', 'travis'),
            ('.circleci/config.yml', 'circleci'),
            ('Jenkinsfile', 'jenkins'),
            ('azure-pipelines.yml', 'azure_pipelines'),
            ('.gitlab-ci.yml', 'gitlab_ci'),
            ('bitbucket-pipelines.yml', 'bitbucket'),
            ('.buildkite/pipeline.yml', 'buildkite'),
            ('Makefile', None),
        ]
        for filename, ci_name in other_ci_files:
            p = root / filename
            if p.is_file():
                parsed = _parse_generic_ci(p)
                if parsed and (parsed['has_tests'] or parsed['has_lint'] or parsed['has_deploy']):
                    if ci_name:
                        system = ci_name
                    workflows.append(parsed)
                    break

    if not workflows and structure.get('ci_systems'):
        system = structure['ci_systems'][0] if structure['ci_systems'] else None

    summary = {
        'has_tests': any(w['has_tests'] for w in workflows),
        'has_lint': any(w['has_lint'] for w in workflows),
        'has_deploy': any(w['has_deploy'] for w in workflows),
        'has_matrix': any(w.get('uses_matrix', False) for w in workflows),
    }

    if not workflows:
        score = 0
    else:
        score = 40
        if summary['has_tests']:
            score += 30
        if summary['has_lint']:
            score += 15
        if summary['has_deploy']:
            score += 10
        if summary['has_matrix']:
            score += 5
        score = min(100, score)

    return {
        'system': system,
        'workflow_count': len(workflows),
        'workflows': workflows,
        'summary': summary,
        'score': score,
    }
