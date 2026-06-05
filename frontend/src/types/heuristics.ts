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
  | 'license_risk'
  | 'complexity_debt'
  | 'test_coverage'
  | 'cicd_maturity'
  | 'container_hygiene'

export interface HeuristicSignal {
  signal: HeuristicSignalKey
  label: string
  score: number
  confidence: 'low' | 'medium' | 'high'
  description: string
  items?: string[]
}

export interface HeuristicDelta {
  signal: string
  label: string
  before: number
  after: number
  delta: number
  direction: 'up' | 'down' | 'same'
}
