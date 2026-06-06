import re

_IMPORT_RE = re.compile(r'^\s*(?:alias|require|import|use)\s+([\w.]+)', re.MULTILINE)

_STDLIB = frozenset({
    'Kernel', 'Enum', 'List', 'Map', 'MapSet', 'String', 'IO', 'File',
    'Path', 'Process', 'Agent', 'GenServer', 'GenEvent', 'Supervisor',
    'Task', 'Stream', 'Range', 'Regex', 'Date', 'Time', 'DateTime',
    'NaiveDateTime', 'Calendar', 'Access', 'Application', 'Atom', 'Base',
    'Behaviour', 'Bitwise', 'Code', 'Dict', 'Duration', 'DynamicSupervisor',
    'Exception', 'Float', 'Function', 'HashDict', 'HashSet', 'Integer',
    'Keyword', 'Logger', 'Macro', 'Module', 'Node', 'Port', 'Protocol',
    'Record', 'Registry', 'Set', 'System', 'Tuple', 'URI', 'Version',
    'Mix', 'ExUnit', 'IEx',
})


def _is_external(dep: str) -> bool:
    return dep.split('.')[0] in _STDLIB


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))]
