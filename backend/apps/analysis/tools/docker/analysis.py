from ...container_analysis import analyze_containers


def analyze(repo_dir: str) -> dict:
    return analyze_containers(repo_dir)
