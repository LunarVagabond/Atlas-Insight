import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OverviewPanel from '../components/analysis/OverviewPanel.vue'
import type { RunResult } from '../stores/analysis'

const stubs = {
  AppCard: { template: '<div class="card"><slot /></div>' },
  AppBadge: { template: '<span class="badge"><slot /></span>', props: ['variant'] },
  ConstellationPanel: { template: '<div />' },
}

function makeResult(overrides: Partial<RunResult> = {}): RunResult {
  return {
    commits: {
      total_commits: 120,
      total_contributors: 4,
      abandoned: false,
      days_since_last_commit: 10,
      monthly_frequency: [],
    },
    heuristics: [
      { signal: 'burnout', label: 'Burnout', score: 20, confidence: 'high', description: 'Low burnout risk' },
      { signal: 'ci_health', label: 'CI Health', score: 40, confidence: 'medium', description: 'CI needs attention' },
    ],
    structure: { total_lines: 8000, bus_factor: 3 },
    github_meta: { archived: false },
    security: { issue_count: 0, vulnerabilities: [] },
    ownership: { bus_factor: 3 },
    graph: { god_modules: [] },
    contribution_opportunities: [],
    classification: null,
    repo_type: { sub_projects: [] },
    ...overrides,
  } as unknown as RunResult
}

describe('OverviewPanel — stat cards', () => {
  it('renders total commits', () => {
    const w = mount(OverviewPanel, { props: { result: makeResult() }, global: { stubs } })
    expect(w.text()).toContain('120')
    expect(w.text()).toContain('Total Commits')
  })

  it('renders total contributors', () => {
    const w = mount(OverviewPanel, { props: { result: makeResult() }, global: { stubs } })
    expect(w.text()).toContain('4')
    expect(w.text()).toContain('Contributors')
  })

  it('renders lines of code when structure.total_lines present', () => {
    const w = mount(OverviewPanel, { props: { result: makeResult() }, global: { stubs } })
    expect(w.text()).toContain('8,000')
    expect(w.text()).toContain('Lines of Code')
  })

  it('hides lines of code card when structure.total_lines absent', () => {
    const result = makeResult({ structure: { total_lines: 0, bus_factor: 1 } } as Partial<RunResult>)
    const w = mount(OverviewPanel, { props: { result }, global: { stubs } })
    expect(w.text()).not.toContain('Lines of Code')
  })

  it('shows overall risk score badge', () => {
    // scores 20 + 40 → avg = 30
    const w = mount(OverviewPanel, { props: { result: makeResult() }, global: { stubs } })
    expect(w.text()).toContain('Risk: 30/100')
  })
})

describe('OverviewPanel — notable findings', () => {
  it('flags archived repository', () => {
    const result = makeResult({ github_meta: { archived: true } } as Partial<RunResult>)
    const w = mount(OverviewPanel, { props: { result }, global: { stubs } })
    expect(w.text()).toContain('archived')
  })

  it('flags abandoned repository', () => {
    const result = makeResult({
      commits: { total_commits: 10, total_contributors: 1, abandoned: true, days_since_last_commit: 400, monthly_frequency: [] },
    } as Partial<RunResult>)
    const w = mount(OverviewPanel, { props: { result }, global: { stubs } })
    expect(w.text()).toContain('400 days silent')
  })

  it('flags CVEs in dependencies', () => {
    const result = makeResult({
      security: { issue_count: 0, vulnerabilities: [{ name: 'lodash', severity: 'high' }, { name: 'axios', severity: 'medium' }] },
    } as Partial<RunResult>)
    const w = mount(OverviewPanel, { props: { result }, global: { stubs } })
    expect(w.text()).toContain('2 known CVEs')
  })

  it('shows no findings section for a clean repo', () => {
    const result = makeResult({ heuristics: [] })
    const w = mount(OverviewPanel, { props: { result }, global: { stubs } })
    expect(w.find('.overview-findings').exists()).toBe(false)
  })
})

describe('OverviewPanel — sparkline', () => {
  it('renders sparkline when monthly_frequency present', () => {
    const result = makeResult({
      commits: {
        total_commits: 50,
        total_contributors: 2,
        abandoned: false,
        days_since_last_commit: 5,
        monthly_frequency: [
          { month: '2025-06', count: 10 },
          { month: '2025-07', count: 5 },
        ],
      },
    } as Partial<RunResult>)
    const w = mount(OverviewPanel, { props: { result }, global: { stubs } })
    expect(w.find('.overview-sparkline').exists()).toBe(true)
  })

  it('hides sparkline when no monthly data', () => {
    const w = mount(OverviewPanel, { props: { result: makeResult() }, global: { stubs } })
    expect(w.find('.overview-sparkline').exists()).toBe(false)
  })
})
