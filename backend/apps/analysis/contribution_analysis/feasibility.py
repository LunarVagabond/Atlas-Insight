from __future__ import annotations

_CATEGORY_DOMAINS: dict[str, list[str]] = {
    'documentation': ['documentation'],
    'community': ['community'],
    'ci': ['devops', 'ci'],
    'testing': ['testing'],
    'security': ['security'],
    'dependencies': ['dependencies'],
}

_FILE_SUBSYSTEM_PREFIXES: dict[str, list[str]] = {
    'frontend': ['src/', 'frontend/', 'client/', 'ui/', 'app/', 'web/', 'pages/', 'components/'],
    'api': ['api/', 'routes/', 'routers/', 'endpoints/', 'views/', 'handlers/', 'controllers/', 'server/'],
    'data': ['models/', 'db/', 'database/', 'migrations/', 'schemas/', 'repositories/'],
    'tests': ['tests/', '__tests__/', 'spec/', 'test/', 'e2e/', 'integration/'],
    'config': ['config/', 'scripts/', '.github/', 'ci/', 'infra/', 'deploy/'],
}


def domain_from_file(path: str) -> str:
    lower = path.lower()
    for domain, prefixes in _FILE_SUBSYSTEM_PREFIXES.items():
        if any(lower.startswith(p) for p in prefixes):
            return domain
    return 'general'


def effort_estimate(difficulty: str, risk: str) -> str:
    if difficulty == 'beginner' and risk == 'low':
        return 'quick-win'
    if (difficulty == 'beginner' and risk == 'medium') or (difficulty == 'intermediate' and risk == 'low'):
        return 'small'
    if difficulty == 'intermediate' and risk == 'medium':
        return 'medium'
    return 'large'


def annotate_feasibility(opps: list[dict]) -> None:
    for opp in opps:
        cat = opp.get('category', '')
        diff = opp.get('difficulty', 'beginner')
        risk = opp.get('risk', 'low')

        if cat in _CATEGORY_DOMAINS:
            domains = _CATEGORY_DOMAINS[cat]
        elif cat == 'refactoring':
            file_hint = ''
            for hint in opp.get('hints', []):
                if hint.startswith('Open `'):
                    file_hint = hint[6:].split('`')[0]
                    break
            domains = [domain_from_file(file_hint)] if file_hint else ['general']
        else:
            domains = []

        opp['knowledge_domains'] = domains
        opp['effort_estimate'] = effort_estimate(diff, risk)

        if opp.get('id', '').startswith('todo_'):
            opp['affected_file_count'] = 1
        elif opp.get('id', '').startswith('revert_hotspot_'):
            opp['affected_file_count'] = 0
        else:
            opp['affected_file_count'] = 0
