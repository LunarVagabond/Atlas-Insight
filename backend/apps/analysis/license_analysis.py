import re
from pathlib import Path

_LICENSE_PATTERNS = [
    ('MIT', r'permission is hereby granted.*?without restriction', 'MIT License', False, True),
    ('Apache-2.0', r'apache license.*?version 2\.0', 'Apache License 2.0', False, True),
    ('GPL-3.0', r'gnu general public license.*?version 3', 'GNU General Public License v3.0', True, True),  # noqa: E501
    ('GPL-2.0', r'gnu general public license.*?version 2', 'GNU General Public License v2.0', True, True),  # noqa: E501
    ('AGPL-3.0', r'gnu affero general public license.*?version 3', 'GNU Affero GPL v3.0', True, True),  # noqa: E501
    ('LGPL-3.0', r'gnu lesser general public license.*?version 3', 'GNU Lesser GPL v3.0', True, True),  # noqa: E501
    ('LGPL-2.1', r'gnu lesser general public license.*?version 2\.1', 'GNU Lesser GPL v2.1', True, True),  # noqa: E501
    ('MPL-2.0', r'mozilla public license.*?version 2\.0', 'Mozilla Public License 2.0', False, True),  # noqa: E501
    ('BSD-3-Clause', r'redistribution and use in source and binary forms.*?neither the name', 'BSD 3-Clause', False, True),  # noqa: E501
    ('BSD-2-Clause', r'redistribution and use in source and binary forms.*?provided that the following', 'BSD 2-Clause', False, True),  # noqa: E501
    ('ISC', r'permission to use.*?isc', 'ISC License', False, True),
    ('Unlicense', r'this is free and unencumbered software', 'The Unlicense', False, True),
    ('CC0-1.0', r'cc0 1\.0 universal|creative commons.*?zero', 'CC0 1.0 Universal', False, True),
    ('EUPL-1.2', r'european union public licence.*?v\.?\s*1\.2', 'European Union Public Licence 1.2', True, True),  # noqa: E501
]

# Static license lookup for common packages (ecosystem -> {package: spdx})
_KNOWN_LICENSES: dict[str, dict[str, str]] = {
    'PyPI': {
        'django': 'BSD-3-Clause', 'flask': 'BSD-3-Clause', 'fastapi': 'MIT',
        'requests': 'Apache-2.0', 'numpy': 'BSD-3-Clause', 'pandas': 'BSD-3-Clause',
        'scipy': 'BSD-3-Clause', 'matplotlib': 'PSF', 'pillow': 'HPND',
        'sqlalchemy': 'MIT', 'celery': 'BSD-3-Clause', 'redis': 'MIT',
        'pydantic': 'MIT', 'pytest': 'MIT', 'black': 'MIT', 'ruff': 'MIT',
        'cryptography': 'Apache-2.0', 'paramiko': 'LGPL-2.1', 'boto3': 'Apache-2.0',
        'stripe': 'MIT', 'httpx': 'BSD-3-Clause', 'uvicorn': 'BSD-3-Clause',
        'gunicorn': 'MIT', 'psycopg2': 'LGPL-3.0', 'psycopg2-binary': 'LGPL-3.0',
        'django-ninja': 'MIT', 'django-rest-framework': 'BSD-3-Clause',
        'python-decouple': 'MIT', 'whitenoise': 'MIT', 'sentry-sdk': 'MIT',
    },
    'npm': {
        'react': 'MIT', 'vue': 'MIT', 'angular': 'MIT', 'svelte': 'MIT',
        'express': 'MIT', 'lodash': 'MIT', 'axios': 'MIT', 'moment': 'MIT',
        'dayjs': 'MIT', 'typescript': 'Apache-2.0', 'webpack': 'MIT',
        'vite': 'MIT', 'rollup': 'MIT', 'eslint': 'MIT', 'prettier': 'MIT',
        'jest': 'MIT', 'vitest': 'MIT', 'tailwindcss': 'MIT', 'next': 'MIT',
        'nuxt': 'MIT', 'pinia': 'MIT', 'vuex': 'MIT', 'react-router-dom': 'MIT',
        'zod': 'MIT', 'uuid': 'MIT', 'dotenv': 'BSD-2-Clause',
        '@vue/core': 'MIT', 'sass': 'MIT', 'autoprefixer': 'MIT',
    },
    'crates.io': {
        'serde': 'MIT/Apache-2.0', 'tokio': 'MIT', 'async-std': 'Apache-2.0',
        'reqwest': 'MIT/Apache-2.0', 'hyper': 'MIT', 'actix-web': 'MIT/Apache-2.0',
        'rocket': 'MIT/Apache-2.0', 'clap': 'MIT/Apache-2.0', 'anyhow': 'MIT/Apache-2.0',
    },
    'RubyGems': {
        'rails': 'MIT', 'sinatra': 'MIT', 'rake': 'MIT', 'rspec': 'MIT',
        'rubocop': 'MIT', 'devise': 'MIT', 'sidekiq': 'LGPL-3.0',
    },
    'Go': {
        'github.com/gin-gonic/gin': 'MIT', 'github.com/gorilla/mux': 'BSD-3-Clause',
        'github.com/stretchr/testify': 'MIT',
    },
}

_COPYLEFT_IDS = {'GPL-2.0', 'GPL-3.0', 'AGPL-3.0', 'LGPL-2.1', 'LGPL-3.0', 'EUPL-1.2'}
_PERMISSIVE_IDS = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'Unlicense', 'CC0-1.0', 'MPL-2.0'}  # noqa: E501
_LICENSE_FILENAMES = {'LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE', 'LICENCE.md', 'COPYING', 'COPYING.md'}  # noqa: E501


def _detect_spdx_from_file(repo_dir: str) -> tuple[str | None, str | None, str | None]:
    root = Path(repo_dir)
    for name in _LICENSE_FILENAMES:
        path = root / name
        if path.is_file():
            try:
                text = path.read_text(errors='ignore')[:8000].lower()
                for spdx, pattern, human_name, _, _ in _LICENSE_PATTERNS:
                    if re.search(pattern, text, re.DOTALL | re.IGNORECASE):
                        return spdx, human_name, name
            except OSError:
                pass
    return None, None, None


def _lookup_dep_license(dep_name: str, ecosystem: str) -> str | None:
    ecosystem_map = _KNOWN_LICENSES.get(ecosystem, {})
    return ecosystem_map.get(dep_name.lower()) or ecosystem_map.get(dep_name)


def _is_compatible(dep_spdx: str, project_spdx: str | None) -> bool | None:
    if project_spdx is None:
        return None
    dep_copyleft = any(c in dep_spdx for c in ('GPL', 'AGPL', 'LGPL', 'EUPL'))
    proj_permissive = project_spdx in _PERMISSIVE_IDS
    if dep_copyleft and proj_permissive:
        return False
    return True


def analyze_license(
    repo_dir: str,
    deps: dict,
    github_meta: dict,
    scoring_mode: str = 'oss',
) -> dict:
    spdx_id, human_name, source_file = _detect_spdx_from_file(repo_dir)

    if spdx_id:
        source = 'file'
    elif github_meta.get('license_spdx'):
        spdx_id = github_meta['license_spdx']
        human_name = github_meta.get('license_name') or spdx_id
        source = 'github_api'
    else:
        source = 'none'

    osi_approved = spdx_id in (_PERMISSIVE_IDS | _COPYLEFT_IDS) if spdx_id else False
    copyleft = spdx_id in _COPYLEFT_IDS if spdx_id else False

    dep_list = deps.get('dependencies', [])
    dep_licenses: list[dict] = []
    for dep in dep_list[:100]:
        dep_name = dep.get('name', '')
        ecosystem = dep.get('ecosystem') or dep.get('source', '')
        found_license = _lookup_dep_license(dep_name, ecosystem)
        if found_license:
            compatible = _is_compatible(found_license, spdx_id)
            dep_licenses.append({
                'name': dep_name,
                'license': found_license,
                'compatible': compatible,
            })

    issues: list[dict] = []
    score = 0

    if source == 'none':
        if scoring_mode != 'closed_source':
            issues.append({
                'severity': 'high',
                'message': 'No license file found — repository is implicitly all-rights-reserved',
            })
            score += 60

    incompatible = [d for d in dep_licenses if d['compatible'] is False]
    if incompatible and spdx_id:
        for d in incompatible[:5]:
            issues.append({
                'severity': 'medium',
                'message': f'{d["name"]} ({d["license"]}) may be incompatible with {spdx_id}',
            })
        score += min(30, len(incompatible) * 10)

    if spdx_id and copyleft:
        issues.append({
            'severity': 'low',
            'message': f'{spdx_id} is copyleft — derivative works must use the same license',
        })
        score += 5

    return {
        'spdx_id': spdx_id,
        'name': human_name,
        'osi_approved': osi_approved,
        'copyleft': copyleft,
        'source': source,
        'source_file': source_file,
        'dep_licenses': dep_licenses,
        'issues': issues,
        'score': min(100, score),
    }
