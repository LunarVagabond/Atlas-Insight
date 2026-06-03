export interface MonthlyCommit {
  sha: string
  message: string
  body?: string | null
  author: string
  date: string
  parents?: string[]
}

export interface CommitConventions {
  style: 'conventional_commits' | 'ticket_prefix' | 'jira_prefix' | 'bracket_prefix' | 'emoji_prefix' | 'sentence_case' | 'mixed'
  style_confidence: number
  avg_subject_length: number
  subject_under_72_pct: number
  issue_ref_rate: number
  examples: string[]
  format_template?: string
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
  commit_conventions?: CommitConventions
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
