import type { Classification } from '../stores/analysis'

export interface Archetype {
  icon: string
  label: string
  description: string
}

export function getRepoArchetype(cls: Classification | undefined | null): Archetype | null {
  if (!cls) return null

  const health = cls.project_health.key
  const difficulty = cls.contribution_difficulty.key
  const complexity = cls.code_complexity.key
  const docs = cls.documentation_grade.key
  const tags = cls.tags ?? []

  const has = (t: string) => tags.includes(t)
  const thriving = health === 'thriving' || health === 'active'
  const dormant = health === 'abandoned' || health === 'declining'

  if (has('archived') || health === 'abandoned') {
    return { icon: '💀', label: 'Legacy Codebase', description: 'Inactive or archived — minimal to no ongoing development' }
  }
  if (thriving && (has('wildly-popular') || has('popular'))) {
    return { icon: '🚀', label: 'Rocket Ship', description: 'Thriving project with high community traction and active development' }
  }
  if (thriving && (has('large-community') || has('thriving-community'))) {
    return { icon: '⚡', label: 'Community Powerhouse', description: 'Large active contributor base driving rapid development' }
  }
  if ((docs === 'excellent' || docs === 'good') && (complexity === 'simple' || complexity === 'moderate')) {
    return { icon: '📚', label: 'Well-documented Library', description: 'Clean codebase with strong documentation — easy to learn from' }
  }
  if ((difficulty === 'very_easy' || difficulty === 'easy') && has('welcoming')) {
    return { icon: '🤝', label: 'Contributor-friendly', description: 'Low barrier to entry with good onboarding for new contributors' }
  }
  if (thriving && (complexity === 'very_complex' || complexity === 'complex')) {
    return { icon: '🏗️', label: 'Complex Machine', description: 'Actively developed but architecturally dense — steep learning curve' }
  }
  if (thriving && (complexity === 'simple' || complexity === 'moderate')) {
    return { icon: '🌱', label: 'Growing Project', description: 'Active development with manageable complexity — good momentum' }
  }
  if (health === 'stable') {
    return { icon: '🏛️', label: 'Mature & Stable', description: 'Established project with steady maintenance and low churn' }
  }
  if (dormant) {
    return { icon: '📉', label: 'Winding Down', description: 'Declining activity — may still be useful but development is slowing' }
  }
  return { icon: '🔍', label: 'Under the Radar', description: 'Early-stage or niche project — small but potentially useful' }
}
