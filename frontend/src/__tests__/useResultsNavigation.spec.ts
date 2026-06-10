import { describe, it, expect } from 'vitest'
import {
  resolveTabFromQuery,
  sectionsForTab,
  TAB_SECTIONS,
  LEGACY_TAB_MAP,
  buildNavPositions,
} from '../composables/useResultsNavigation'

const TABS = [
  'Overview', 'Heuristics', 'Security', 'Licenses', 'Dependencies',
  'Architecture', 'Code Quality', 'Repository', 'Roadmap', 'Ownership',
  'Contributing', 'Tours', 'Community Files', 'Leaderboards', 'DevOps',
]

describe('useResultsNavigation helpers', () => {
  it('resolves legacy Project tab to Repository Profile', () => {
    const result = resolveTabFromQuery('Project', undefined, TABS)
    expect(result.tab).toBe('Repository')
    expect(result.section).toBe('Profile')
    expect(LEGACY_TAB_MAP.Project.tab).toBe('Repository')
  })

  it('resolves legacy History tab to Repository Activity', () => {
    const result = resolveTabFromQuery('History', undefined, TABS)
    expect(result.tab).toBe('Repository')
    expect(result.section).toBe('Activity')
  })

  it('resolves legacy Contribution Path to Tours Start Here', () => {
    const result = resolveTabFromQuery('Contribution Path', undefined, TABS)
    expect(result.tab).toBe('Tours')
    expect(result.section).toBe('Start Here')
  })

  it('defaults invalid section to first section for tab', () => {
    const result = resolveTabFromQuery('Architecture', 'Invalid', TABS)
    expect(result.tab).toBe('Architecture')
    expect(result.section).toBe('Explorer')
  })

  it('keeps valid section from query', () => {
    const result = resolveTabFromQuery('Heuristics', 'Signals', TABS)
    expect(result.section).toBe('Signals')
  })

  it('returns null section for tabs without sub-tabs', () => {
    expect(sectionsForTab('Overview')).toBeNull()
    expect(sectionsForTab('Licenses')).toBeNull()
  })

  it('defines sub-tabs for heavy panels', () => {
    expect(TAB_SECTIONS.Architecture).toEqual(['Explorer', 'Graph'])
    expect(TAB_SECTIONS.Repository).toEqual(['Profile', 'Activity', 'Branches'])
    expect(TAB_SECTIONS.Tours).toEqual(['Guided', 'Start Here'])
  })

  it('builds a flat nav list that steps across sectionless tabs', () => {
    const positions = buildNavPositions(TABS)
    const overviewIdx = positions.findIndex(p => p.tab === 'Overview')
    const licensesIdx = positions.findIndex(p => p.tab === 'Licenses')
    const depsIdx = positions.findIndex(p => p.tab === 'Dependencies' && p.section === 'Packages')

    expect(positions[overviewIdx + 1]?.tab).toBe('Heuristics')
    expect(positions[licensesIdx + 1]).toEqual({ tab: 'Dependencies', section: 'Packages' })
    expect(positions[depsIdx - 1]).toEqual({ tab: 'Licenses', section: null })
  })
})
