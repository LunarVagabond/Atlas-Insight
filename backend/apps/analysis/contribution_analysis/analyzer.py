from __future__ import annotations

from .feasibility import annotate_feasibility
from .heuristics import generate_heuristic_opportunities
from .issue_ops import generate_issue_opportunities
from .todo_ops import generate_revert_opportunities, generate_todo_opportunities


def analyze_contributions(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None,
    structure: dict | None,
    security: dict | None,
    contribution_data: dict | None = None,
    todos: dict | None = None,
    scoring_mode: str = 'oss',
) -> list[dict]:
    opps = generate_heuristic_opportunities(
        commits, graph, deps, readme, structure, security, scoring_mode=scoring_mode,
    )
    if todos:
        opps.extend(generate_todo_opportunities(todos))
    opps.extend(generate_revert_opportunities(commits))
    if contribution_data:
        opps.extend(generate_issue_opportunities(contribution_data))
    annotate_feasibility(opps)
    return opps
