import type { CommitData } from './commits'
import type { GraphData, DepsData } from './graph'
import type { HeuristicSignal } from './heuristics'
import type { OssScore, Classification } from './classification'
import type { ReadmeData } from './readme'
import type { StructureData } from './structure'
import type { SecurityData } from './security'
import type { GitHubMeta } from './github'
import type { ContributionOpportunity, ArchTour } from './contributions'
import type { TodoData } from './todos'
import type { OwnershipData } from './ownership'
import type { JitIssue, JitPrData } from './jit'
import type { DiffData } from './diff'

export interface SubProject {
  name: string
  path: string
  languages: string[]
  tech_stack: string[]
  dependencies: DepsData
  graph: GraphData
  security: SecurityData
  heuristics: HeuristicSignal[]
  oss_score?: OssScore
}

export interface RepoTypeInfo {
  type: 'single' | 'fullstack' | 'monorepo' | 'microservices'
  detected_by: string[]
  sub_projects: SubProject[]
}

export interface LicenseDepEntry {
  name: string
  license: string | null
  compatible: boolean | null
}

export interface LicenseIssue {
  severity: 'high' | 'medium' | 'low'
  message: string
}

export interface LicenseData {
  spdx_id: string | null
  name: string | null
  osi_approved: boolean
  copyleft: boolean
  source: 'file' | 'github_api' | 'none'
  source_file: string | null
  dep_licenses: LicenseDepEntry[]
  issues: LicenseIssue[]
  score: number
}

export interface ComplexityHotspot {
  file: string
  loc: number
  has_adjacent_test: boolean
}

export interface ComplexityData {
  hotspots: ComplexityHotspot[]
  avg_file_loc: number
  files_over_threshold: number
  threshold: number
  distribution: { '0-100': number; '100-300': number; '300-500': number; '500+': number }
  score: number
}

export interface DeadCodeEntry {
  file: string
  lang: string
}

export interface DeadCodeData {
  unreferenced: DeadCodeEntry[]
  count: number
  filtered_entry_points: number
  note: string | null
}

export interface UntestedDir {
  path: string
  source_files: number
}

export interface TestCoverageData {
  test_ratio: number
  test_file_count: number
  source_file_count: number
  framework_detected: string | null
  untested_dirs: UntestedDir[]
  well_tested_dirs: number
  score: number
}

export interface ContainerIssue {
  severity: 'high' | 'medium' | 'low'
  line: number | null
  message: string
}

export interface DockerfileResult {
  path: string
  issues: ContainerIssue[]
  is_multistage: boolean
  runs_as_root: boolean
}

export interface ComposeResult {
  path: string
  issues: ContainerIssue[]
}

export interface ContainerData {
  dockerfiles: DockerfileResult[]
  compose_files: ComposeResult[]
  dockerfile_count: number
  compose_count: number
  total_issues: number
  score: number
}

export interface CicdWorkflow {
  name: string
  triggers: string[]
  has_tests: boolean
  has_lint: boolean
  has_deploy: boolean
  has_container_build: boolean
  job_count: number
  uses_matrix: boolean
}

export interface CicdData {
  system: string | null
  workflow_count: number
  workflows: CicdWorkflow[]
  summary: {
    has_tests: boolean
    has_lint: boolean
    has_deploy: boolean
    has_matrix: boolean
  }
  score: number
}

export interface ChangelogIssue {
  severity: 'high' | 'medium' | 'low'
  message: string
}

export interface ChangelogData {
  found: boolean
  filename: string | null
  format: 'keep-a-changelog' | 'versioned' | 'prose' | 'none'
  entry_count: number
  last_entry_date: string | null
  last_entry_version: string | null
  days_stale: number | null
  issues: ChangelogIssue[]
}

export interface RunResult {
  is_docs_only?: boolean
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
  repo_type?: RepoTypeInfo
  license?: LicenseData
  complexity?: ComplexityData
  dead_code?: DeadCodeData
  test_coverage?: TestCoverageData
  containers?: ContainerData
  cicd?: CicdData
  changelog?: ChangelogData
  // Baked in at scan time — no JIT fetching needed
  issues?: JitIssue[]
  pr_refs?: JitPrData['pr_issue_refs']
  diff?: DiffData
  similar_runs?: SimilarRun[]
  error?: string
}

export interface AnalysisRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress_step: '' | 'cloning' | 'parsing' | 'heuristics' | 'metadata' | 'finalizing'
  triggered_at: string
  completed_at: string | null
  result: RunResult | null
  repo_url: string
  repo_owner: string
  repo_name: string
  branch: string
  is_stale: boolean
  is_private: boolean
  last_fetched_at: string | null
  auth_token_warning: string
  cooldown_until: string | null
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
  primary_language: string | null
  top_languages: { name: string; pct: number }[]
  oss_score: number | null
  oss_badge: 'champion' | 'thriving' | 'growing' | 'seedling' | 'struggling' | 'dormant' | null
  scanned_branch_count: number
  cached_branch_count: number | null
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

export interface SimilarRun {
  run_id: string
  owner: string
  name: string
  repo_url: string
  oss_score: number
  health_key: string
  primary_language: string | null
  stars: number
}
