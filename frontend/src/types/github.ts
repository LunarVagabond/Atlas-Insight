export interface GitHubContributor {
  login: string
  avatar_url: string
  html_url: string
  contributions: number
}

export interface GitHubMeta {
  html_url: string | null
  stars: number
  forks: number
  open_issues: number
  open_prs: number | null
  watchers: number
  primary_language: string | null
  topics: string[]
  license_spdx: string | null
  license_name: string | null
  github_description: string | null
  size_kb: number
  default_branch: string
  has_wiki: boolean
  has_discussions: boolean
  archived: boolean
  is_fork: boolean
  created_at: string | null
  pushed_at: string | null
  homepage: string | null
  contributors: GitHubContributor[]
  releases_meta?: {
    total_count: number
    latest_release: { name: string; date: string } | null
  }
}
