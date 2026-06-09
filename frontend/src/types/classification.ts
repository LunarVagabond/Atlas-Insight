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

export interface ClassificationDelta {
  before_label: string
  after_label: string
  delta: number
  changed: boolean
}

export type ScoringMode = 'oss' | 'closed_source'

export interface OssScore {
  score: number
  badge: 'champion' | 'thriving' | 'growing' | 'seedling' | 'struggling' | 'dormant'
  label: string
  mode?: ScoringMode
}
