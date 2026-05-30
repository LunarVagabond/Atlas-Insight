import { defineStore } from 'pinia'
import axios from 'axios'

export interface AnalysisRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  result: RunResult | null
  repo_url: string
  repo_owner: string
  repo_name: string
  is_stale: boolean
  last_fetched_at: string | null
  auth_token_warning: string
}

export interface RoadmapMilestone {
  title: string
  date: string | null
  status: 'done' | 'in-progress' | 'planned'
  done_count: number
  todo_count: number
  done_items: string[]
  todo_items: string[]
}

export interface ContributionOpportunity {
  id: string
  title: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  risk: 'low' | 'medium' | 'high'
  category: 'documentation' | 'testing' | 'ci' | 'community' | 'refactoring' | 'security' | 'dependencies' | 'github-issue' | 'feature'
  issue_url?: string
  issue_number?: number
  has_open_pr?: boolean
  labels?: string[]
  hints?: string[]
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
  contribution_opportunities?: ContributionOpportunity[]
  error?: string
}

export interface ReadmeData {
  found: boolean
  filename: string | null
  content: string | null
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
  pct: number
  files?: number
  lines?: number
  bytes?: number
}

export interface CommunityFilesContent {
  contributing: string | null
  license: string | null
  coc: string | null
  security: string | null
  changelog: string | null
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
  coc_file: string | null
  has_security_policy: boolean
  security_policy_file: string | null
  has_changelog: boolean
  changelog_file: string | null
  roadmap_file?: string | null
  roadmap_parsed?: {
    milestones: RoadmapMilestone[]
  } | null
  community_files_content: CommunityFilesContent
  releases: { name: string; date: string }[]
  release_count: number
  last_release: { name: string; date: string } | null
  repo_age_days: number | null
  bus_factor: number
  top_contributors: { author: string; files_touched: number }[]
  hot_files: { file: string; commit_count: number }[]
  tech_stack?: string[]
  all_files?: string[]
}

export interface SecurityData {
  issues: { severity: string; type: string; detail: string }[]
  issue_count: number
  score: number
  gitignore_exists: boolean
  gitignore_gaps: string[]
}

export interface GitHubContributor {
  login: string
  avatar_url: string
  html_url: string
  contributions: number
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
  contributors: GitHubContributor[]
  releases_meta?: {
    stable_count: number
    prerelease_count: number
    total_count: number
    latest_stable: { name: string; date: string } | null
    latest_prerelease: { name: string; date: string } | null
  }
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

export type HeuristicSignalKey =
  | 'burnout'
  | 'abandonment_risk'
  | 'monolith_growth'
  | 'dependency_health'
  | 'documentation_quality'
  | 'ci_health'
  | 'bus_factor_risk'
  | 'security_hygiene'
  | 'release_cadence'
  | 'community_health'
  | 'commit_velocity'

export interface HeuristicSignal {
  signal: HeuristicSignalKey
  label: string
  score: number
  confidence: 'low' | 'medium' | 'high'
  description: string
  items?: string[]
}

export interface RunListItem {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  repo_url: string
  repo_owner: string
  repo_name: string
  is_stale: boolean
  last_fetched_at: string | null
  tags: string[]
}

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    url: '' as string,
    currentRunId: null as string | null,
    status: 'idle' as 'idle' | 'submitting' | 'polling' | 'done' | 'error',
    run: null as AnalysisRun | null,
    staleRun: null as AnalysisRun | null,
    error: null as string | null,
    _pollInterval: null as ReturnType<typeof setInterval> | null,
  }),

  actions: {
    async submitUrl(url: string, pat?: string) {
      this.url = url
      this.status = 'submitting'
      this.error = null
      this.run = null
      try {
        const { data } = await axios.post('/api/v1/repositories/analyze', { url, pat: pat || undefined })
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
      if (this.run?.status === 'completed') {
        this.staleRun = this.run
      }
      this.run = null
      this.error = null
      this.status = 'polling'
      await this._fetchRun(runId)
      const run = this.run as AnalysisRun | null
      if (!run || (run.status !== 'completed' && run.status !== 'failed')) {
        this._startPolling(runId)
      } else {
        this.status = run.status === 'completed' ? 'done' : 'error'
        if (run.status === 'failed') {
          this.error = run.result?.error ?? 'Analysis failed'
        }
      }
    },

    _startPolling(runId: string) {
      this._stopPolling()
      this._pollInterval = setInterval(async () => {
        await this._fetchRun(runId)
        if (this.run?.status === 'completed') {
          this.status = 'done'
          this.staleRun = null
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

    async retryRun(runId: string): Promise<string> {
      const { data } = await axios.post(`/api/v1/repositories/runs/${runId}/retry`)
      return data.run_id as string
    },

    async deleteRun(runId: string) {
      await axios.delete(`/api/v1/repositories/runs/${runId}`)
    },

    clearRun() {
      this._stopPolling()
      this.url = ''
      this.currentRunId = null
      this.status = 'idle'
      this.run = null
      this.staleRun = null
      this.error = null
    },
  },
})
