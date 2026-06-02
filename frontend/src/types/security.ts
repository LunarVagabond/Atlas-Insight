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
