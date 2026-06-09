export interface LinkSignal {
  label: string
  url: string
  source: string
  description?: string
  platform?: string
}

export interface ReadmeRecommendation {
  id: string
  category: string
  status: 'missing' | 'needs_improvement'
  title: string
  description: string
  score_gain: number
  hints: string[]
}

export interface ReadmeQuality {
  score: number
  potential_score: number
  categories: { key: string; weight: number; score: number; weighted_score: number }[]
  recommendations: ReadmeRecommendation[]
}

export interface ReadmeData {
  found: boolean
  filename: string | null
  content: string | null
  description: string | null
  sections: string[]
  badge_count: number
  word_count: number
  code_block_count?: number
  has_external_links?: boolean
  shallow_sections?: string[]
  has_installation: boolean
  has_usage: boolean
  has_contributing: boolean
  has_changelog: boolean
  has_license: boolean
  has_api_docs: boolean
  docs_links: LinkSignal[]
  social_links: LinkSignal[]
  quality?: ReadmeQuality
}
