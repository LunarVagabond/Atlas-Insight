import { defineStore } from 'pinia'
import axios from 'axios'

export interface AnalysisRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  result: RunResult | null
}

export interface RunResult {
  commits: CommitData
  graph: GraphData
  dependencies: DepsData
  heuristics: HeuristicSignal[]
  readme?: ReadmeData
  structure?: StructureData
  security?: SecurityData
  github_meta?: GitHubMeta
  classification?: Classification
  error?: string
}

export interface ReadmeData {
  found: boolean
  filename: string | null
  description: string | null
  sections: string[]
  badge_count: number
  word_count: number
  has_installation: boolean
  has_usage: boolean
  has_contributing: boolean
  has_changelog: boolean
  has_license: boolean
  has_api_docs: boolean
}

export interface LanguageInfo {
  name: string
  files: number
  lines: number
  pct: number
}

export interface StructureData {
  total_files: number
  total_lines: number
  languages: LanguageInfo[]
  test_files: number
  test_ratio: number
  has_ci: boolean
  ci_systems: string[]
  gh_workflow_count: number
  has_docker: boolean
  has_lint_config: boolean
  has_contributing: boolean
  contributing_file: string | null
  license_file: string | null
  license_type: string | null
  has_coc: boolean
  has_security_policy: boolean
  has_changelog: boolean
  releases: { name: string; date: string }[]
  release_count: number
  last_release: { name: string; date: string } | null
  repo_age_days: number | null
  bus_factor: number
  top_contributors: { author: string; files_touched: number }[]
}

export interface SecurityData {
  issues: { severity: string; type: string; detail: string }[]
  issue_count: number
  score: number
  gitignore_exists: boolean
  gitignore_gaps: string[]
}

export interface GitHubMeta {
  stars: number
  forks: number
  open_issues: number
  open_prs: number | null
  watchers: number
  primary_language: string | null
  topics: string[]
  license_spdx: string | null
  license_name: string | null
  github_description: string | null
  size_kb: number
  default_branch: string
  has_wiki: boolean
  has_discussions: boolean
  archived: boolean
  is_fork: boolean
  created_at: string | null
  pushed_at: string | null
  homepage: string | null
}

export interface ClassificationLevel {
  key: string
  label: string
  score: number
}

export interface Classification {
  contribution_difficulty: ClassificationLevel
  project_health: ClassificationLevel
  code_complexity: ClassificationLevel
  documentation_grade: ClassificationLevel
  tags: string[]
}

export interface CommitData {
  total_commits: number
  total_contributors: number
  last_commit_date: string | null
  days_since_last_commit: number | null
  abandoned: boolean
  activity_decay_ratio: number
  weekly_frequency: { week: string; count: number }[]
  monthly_frequency: { month: string; count: number }[]
  contributor_churn: { month: string; active: number; new: number; lost: number }[]
}

export interface GraphData {
  node_count: number
  edge_count: number
  cycles: string[][]
  cycle_count: number
  god_modules: { module: string; in_degree: number }[]
  hotspots: { file: string; degree: number }[]
  nodes: { id: string; in_degree: number }[]
  edges: { source: string; target: string }[]
}

export interface DepsData {
  dependencies: { name: string; version_spec: string; source: string; dev?: boolean }[]
  dependency_count: number
  docker_issues: { file: string; issue: string }[]
  missing_lockfile_warnings: string[]
}

export interface HeuristicSignal {
  signal: string
  label: string
  score: number
  confidence: 'low' | 'medium' | 'high'
  description: string
}

export interface RunListItem {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  repo_url: string
  repo_owner: string
  repo_name: string
}

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    url: '' as string,
    currentRunId: null as string | null,
    status: 'idle' as 'idle' | 'submitting' | 'polling' | 'done' | 'error',
    run: null as AnalysisRun | null,
    error: null as string | null,
    _pollInterval: null as ReturnType<typeof setInterval> | null,
  }),

  actions: {
    async submitUrl(url: string) {
      this.url = url
      this.status = 'submitting'
      this.error = null
      this.run = null
      try {
        const { data } = await axios.post('/api/v1/repositories/analyze', { url })
        this.currentRunId = data.run_id
        this.status = 'polling'
        this._startPolling(data.run_id)
        return data.run_id as string
      } catch (err: unknown) {
        this.status = 'error'
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        this.error = axiosErr.response?.data?.detail ?? 'Failed to submit URL'
        throw err
      }
    },

    async pollRun(runId: string) {
      this.currentRunId = runId
      this.status = 'polling'
      await this._fetchRun(runId)
      if (this.run?.status !== 'completed' && this.run?.status !== 'failed') {
        this._startPolling(runId)
      } else {
        this.status = this.run.status === 'completed' ? 'done' : 'error'
        if (this.run.status === 'failed') {
          this.error = this.run.result?.error ?? 'Analysis failed'
        }
      }
    },

    _startPolling(runId: string) {
      this._stopPolling()
      this._pollInterval = setInterval(async () => {
        await this._fetchRun(runId)
        if (this.run?.status === 'completed') {
          this.status = 'done'
          this._stopPolling()
        } else if (this.run?.status === 'failed') {
          this.status = 'error'
          this.error = this.run.result?.error ?? 'Analysis failed'
          this._stopPolling()
        }
      }, 3000)
    },

    _stopPolling() {
      if (this._pollInterval) {
        clearInterval(this._pollInterval)
        this._pollInterval = null
      }
    },

    async _fetchRun(runId: string) {
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}`)
        this.run = data
      } catch (err: unknown) {
        this.status = 'error'
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        this.error = axiosErr.response?.data?.detail ?? 'Failed to fetch run'
        this._stopPolling()
      }
    },

    clearRun() {
      this._stopPolling()
      this.url = ''
      this.currentRunId = null
      this.status = 'idle'
      this.run = null
      this.error = null
    },
  },
})
