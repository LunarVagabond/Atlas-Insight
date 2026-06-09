export interface RoadmapMilestone {
  title: string
  date: string | null
  status: 'done' | 'in-progress' | 'planned'
  done_count: number
  todo_count: number
  done_items: string[]
  todo_items: string[]
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

export interface CommunityHealthRecommendation {
  id: string
  file: string
  status: 'missing' | 'needs_improvement'
  title: string
  description: string
  score_gain: number
  hints: string[]
}

export interface CommunityFileHealth {
  key: string
  label: string
  present: boolean
  score: number
  weight: number
  weighted_score: number
  gap: number
}

export interface CommunityHealth {
  score: number
  potential_score: number
  files: CommunityFileHealth[]
  breakdown: CommunityFileHealth[]
  recommendations: CommunityHealthRecommendation[]
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
  community_health?: CommunityHealth
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
  docs_dir?: string | null
}
