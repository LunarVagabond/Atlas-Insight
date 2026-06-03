#!/usr/bin/env python3
"""
Generate contributors_stats.json from git log.

Run at Docker build time (before the git directory is excluded) so the
container has pre-baked contributor stats without needing a live git repo.

Usage:
    python scripts/build_contributor_stats.py
    python scripts/build_contributor_stats.py --output /path/to/contributors_stats.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def build_stats(repo_root: Path) -> dict:
    try:
        out = subprocess.check_output(
            ['git', 'log', '--numstat', '--no-merges', '--format=COMMIT\t%ae\t%an'],
            cwd=str(repo_root),
            text=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f'ERROR: git log failed: {e}', file=sys.stderr)
        sys.exit(1)

    authors: dict = {}
    current_email = ''
    current_name = ''

    for line in out.splitlines():
        if line.startswith('COMMIT\t'):
            parts = line.split('\t', 2)
            current_email = parts[1].lower() if len(parts) > 1 else ''
            current_name = parts[2] if len(parts) > 2 else ''
            if current_email and current_email not in authors:
                authors[current_email] = {
                    'name': current_name,
                    'email': current_email,
                    'lines_added': 0,
                    'lines_removed': 0,
                    'commit_count': 0,
                    'contrib_only_lines': 0,
                }
            if current_email:
                authors[current_email]['commit_count'] += 1
        elif line and current_email:
            parts = line.split('\t')
            if len(parts) == 3:
                try:
                    added = int(parts[0])
                    removed = int(parts[1])
                except ValueError:
                    continue
                file_path = parts[2]
                authors[current_email]['lines_added'] += added
                authors[current_email]['lines_removed'] += removed
                if file_path.startswith('contributors/'):
                    authors[current_email]['contrib_only_lines'] += added

    return authors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(Path(__file__).parent.parent / 'contributors_stats.json'))
    args = parser.parse_args()

    stats = build_stats(REPO_ROOT)
    out_path = Path(args.output)
    out_path.write_text(json.dumps(stats, indent=2))
    print(f'Wrote {len(stats)} author(s) to {out_path}')


if __name__ == '__main__':
    main()
