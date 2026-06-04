export interface PrImpactSubsystem {
  id: string
  name: string
  subsystem_type: string
  activity_score: number
  has_god_modules: boolean
  matched_files: number
}

export interface PrImpactReviewer {
  author: string
  email: string
  pr_files_touched: number
  match_reason: 'file_history' | 'subsystem_match' | 'top_contributor'
}

export interface PrImpactData {
  pr_number: number
  title: string
  state: string
  pr_url: string
  author: string
  additions: number
  deletions: number
  files_changed: number
  complexity_score: number
  complexity_label: 'low' | 'medium' | 'high'
  touches_god_module: boolean
  touches_deps: boolean
  complexity_notes: string[]
  affected_subsystems: PrImpactSubsystem[]
  suggested_reviewers: PrImpactReviewer[]
}
