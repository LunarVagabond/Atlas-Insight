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
