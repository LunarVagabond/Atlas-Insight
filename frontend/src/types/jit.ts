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
