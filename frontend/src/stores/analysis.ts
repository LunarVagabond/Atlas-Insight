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
  is_private: boolean
  last_fetched_at: string | null
  auth_token_warning: string
  cooldown_until: string | null
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
  knowledge_domains?: string[]
  effort_estimate?: 'quick-win' | 'small' | 'medium' | 'large'
  affected_file_count?: number
  readiness_score?: number
  readiness_label?: string
}

export interface HeuristicDelta {
  signal: string
  label: string
  before: number
  after: number
  delta: number
  direction: 'up' | 'down' | 'same'
}

export interface ClassificationDelta {
  before_label: string
  after_label: string
  delta: number
  changed: boolean
}

export interface DiffData {
  available: boolean
  previous_run_id?: string
  previous_triggered_at?: string
  heuristics?: HeuristicDelta[]
  dependencies?: { added: string[]; removed: string[]; added_count: number; removed_count: number }
  contributors?: { before: number; after: number; delta: number }
  graph?: { nodes_before: number; nodes_after: number; nodes_delta: number; god_modules_before: number; god_modules_after: number; god_modules_delta: number }
  structure?: { files_before: number; files_after: number; files_delta: number; test_ratio_before: number; test_ratio_after: number }
  classification?: { project_health?: ClassificationDelta | null; contribution_difficulty?: ClassificationDelta | null; documentation_grade?: ClassificationDelta | null; code_complexity?: ClassificationDelta | null }
}

export interface FileHistoryCommit {
  sha: string
  full_sha: string
  message: string
  date: string
  author: string
  url: string
  issue_refs: number[]
}

export interface FileHistory {
  path: string
  commits: FileHistoryCommit[]
}

export interface JitIssue {
  number: number
  title: string
  url: string
  labels: string[]
  body_excerpt: string
}

export interface JitPrData {
  pr_issue_refs: number[]
  open_prs: number
}

export interface OwnershipSubsystem {
  id: string
  name: string
  subsystem_type: string
  file_count: number
  activity_score: number
  hot_files: { file: string; commit_count: number }[]
  god_modules: { module: string; in_degree: number }[]
  primary_language: string
}

export interface OwnershipData {
  subsystems: OwnershipSubsystem[]
  top_contributors: { author: string; email?: string; files_touched: number }[]
  bus_factor: number
}

export interface OssScore {
  score: number
  badge: 'champion' | 'thriving' | 'growing' | 'seedling' | 'struggling' | 'dormant'
  label: string
}

export interface RunResult {
  commits: CommitData
  graph: GraphData
  dependencies: DepsData
  heuristics: HeuristicSignal[]
  oss_score?: OssScore
  readme?: ReadmeData
  structure?: StructureData
  security?: SecurityData
  github_meta?: GitHubMeta
  classification?: Classification
  contribution_opportunities?: ContributionOpportunity[]
  todos?: TodoData
  arch_tours?: ArchTour[]
  ownership?: OwnershipData
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
  docs_links: LinkSignal[]
  social_links: LinkSignal[]
}

export interface LinkSignal {
  label: string
  url: string
  source: string
  description?: string
  platform?: string
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
  top_contributors: { author: string; email?: string; files_touched: number }[]
  hot_files: { file: string; commit_count: number }[]
  tech_stack?: string[]
  all_files?: string[]
  stale_branches?: { name: string; last_commit: string; days_ago: number }[]
  stale_branch_count?: number
}

export interface VulnFinding {
  name: string
  version: string
  ecosystem: string
  vuln_id: string
  summary: string
  severity: string | null
  url: string
}

export interface SecurityData {
  issues: { severity: string; type: string; detail: string }[]
  issue_count: number
  score: number
  gitignore_exists: boolean
  gitignore_gaps: string[]
  vulnerabilities?: VulnFinding[]
}

export interface GitHubContributor {
  login: string
  avatar_url: string
  html_url: string
  contributions: number
}

export interface GitHubMeta {
  html_url: string | null
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

export interface TodoItem {
  file: string
  line: number
  type: string
  text: string
}

export interface TodoData {
  total: number
  by_type: Record<string, number>
  items: TodoItem[]
}

export interface ArchTourFile {
  file: string
  commit_count?: number
}

export interface ArchTourStep {
  file: string
  note: string
}

export interface ArchTour {
  id: string
  name: string
  description: string
  subsystem_type: string
  file_count: number
  entry_files: string[]
  key_files: ArchTourFile[]
  reading_order: ArchTourStep[]
}

export interface FeaturedRepo {
  run_id: string
  repo_url: string
  repo_owner: string
  repo_name: string
  stars: number | null
  health_label: string | null
  health_key: string | null
  primary_language: string | null
  topics: string[]
  github_description: string | null
}

export interface MonthlyCommit {
  sha: string
  message: string
  body?: string | null
  author: string
  date: string
  parents?: string[]
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
  monthly_commits?: Record<string, MonthlyCommit[]>
  reverted_commits?: { sha: string; message: string; date: string; files: string[] }[]
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
  dependencies: { name: string; version_spec: string; source: string; dev?: boolean; version?: string; ecosystem?: string }[]
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
  repo_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  repo_url: string
  repo_owner: string
  repo_name: string
  is_stale: boolean
  is_private: boolean
  is_favorited: boolean
  last_fetched_at: string | null
  tags: string[]
  has_previous_run: boolean
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
    jitIssues: null as JitIssue[] | null,
    jitPrs: null as JitPrData | null,
    jitLoading: false,
    jitError: false,
    diffData: null as DiffData | null,
    diffLoading: false,
  }),

  actions: {
    async submitUrl(url: string, pat?: string, notificationEmail?: string) {
      this.url = url
      this.status = 'submitting'
      this.error = null
      this.run = null
      this.staleRun = null
      try {
        const { data } = await axios.post('/api/v1/repositories/analyze', {
          url,
          pat: pat || undefined,
          notification_email: notificationEmail || undefined,
        })
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

    async fetchJitData(runId: string) {
      if (this.jitLoading) return
      this.jitLoading = true
      this.jitError = false
      try {
        const [issuesRes, prsRes] = await Promise.allSettled([
          axios.get(`/api/v1/repositories/runs/${runId}/issues`),
          axios.get(`/api/v1/repositories/runs/${runId}/prs`),
        ])
        this.jitIssues = issuesRes.status === 'fulfilled' ? issuesRes.value.data : null
        this.jitPrs = prsRes.status === 'fulfilled' ? prsRes.value.data : null
        if (issuesRes.status === 'rejected' && prsRes.status === 'rejected') {
          this.jitError = true
        }
      } finally {
        this.jitLoading = false
      }
    },

    async fetchDiff(runId: string) {
      if (this.diffLoading) return
      this.diffLoading = true
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/diff`)
        this.diffData = data
      } catch {
        this.diffData = { available: false }
      } finally {
        this.diffLoading = false
      }
    },

    async fetchFileHistory(runId: string, path: string): Promise<FileHistory | null> {
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/file-history`, { params: { path } })
        return data as FileHistory
      } catch {
        return null
      }
    },

    async pollRun(runId: string) {
      this.currentRunId = runId
      this.staleRun = null
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
      this.diffData = null
      this.jitIssues = null
      this.jitPrs = null
      this.jitError = false
    },
  },
})
