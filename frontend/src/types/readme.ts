export interface LinkSignal {
  label: string
  url: string
  source: string
  description?: string
  platform?: string
}

export interface ReadmeData {
  found: boolean
  filename: string | null
  content: string | null
  description: string | null
  sections: string[]
  badge_count: number
  word_count: number
  has_installation: boolean
  has_usage: boolean
  has_contributing: boolean
  has_changelog: boolean
  has_license: boolean
  has_api_docs: boolean
  docs_links: LinkSignal[]
  social_links: LinkSignal[]
}
