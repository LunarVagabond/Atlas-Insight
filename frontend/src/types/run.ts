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
