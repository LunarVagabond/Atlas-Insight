import type { RunResult } from './run'

export interface AnalysisExportV2 {
  export_version: '2'
  exported_at: string
  run: {
    id: string
    repo_owner: string
    repo_name: string
    branch: string
    url: string
    triggered_at: string
    completed_at: string | null
  }
  scoring: {
    mode: RunResult['scoring_mode']
    mode_reason: RunResult['scoring_mode_reason']
    oss_score: RunResult['oss_score']
    heuristics: RunResult['heuristics']
    classification: RunResult['classification']
  }
  repository: {
    readme: RunResult['readme']
    structure: RunResult['structure']
    github_meta: RunResult['github_meta']
    commits: RunResult['commits']
    ownership: RunResult['ownership']
  }
  analysis: {
    graph: RunResult['graph']
    dependencies: RunResult['dependencies']
    security: RunResult['security']
    todos: RunResult['todos']
    contribution_opportunities: RunResult['contribution_opportunities']
    arch_tours: RunResult['arch_tours']
    repo_type: RunResult['repo_type']
  }
  quality: {
    complexity: RunResult['complexity']
    dead_code: RunResult['dead_code']
    test_coverage: RunResult['test_coverage']
    license: RunResult['license']
  }
  devops: {
    cicd: RunResult['cicd']
    containers: RunResult['containers']
    tools: RunResult['tools']
    changelog: RunResult['changelog']
  }
  context: {
    diff: RunResult['diff']
    similar_runs: RunResult['similar_runs']
    issues: RunResult['issues']
    pr_refs: RunResult['pr_refs']
    is_docs_only: RunResult['is_docs_only']
  }
}
