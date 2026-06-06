from .edges import _IMPORT_RE, _is_external


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    return {m.group(1).replace('.', '/') for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))}
