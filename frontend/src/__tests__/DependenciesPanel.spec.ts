import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DependenciesPanel from '../components/analysis/DependenciesPanel.vue'
import type { DepsData, SecurityData } from '../stores/analysis'

const stubs = {
  AppCard: { template: '<div class="card"><slot /></div>' },
  AppBadge: { template: '<span class="badge" :data-variant="variant"><slot /></span>', props: ['variant'] },
  SubProjectSelector: { template: '<div />' },
}

function makeDeps(overrides: Partial<DepsData> = {}): DepsData {
  return {
    dependency_count: 0,
    dependencies: [],
    docker_issues: [],
    missing_lockfile_warnings: [],
    ...overrides,
  }
}

function makeSecurity(overrides: Partial<SecurityData> = {}): SecurityData {
  return {
    issues: [],
    issue_count: 0,
    score: 0,
    gitignore_exists: true,
    gitignore_gaps: [],
    vulnerabilities: [],
    ...overrides,
  }
}

describe('DependenciesPanel — stat cards', () => {
  it('shows dependency count', () => {
    const deps = makeDeps({ dependency_count: 42 })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    expect(w.text()).toContain('42')
    expect(w.text()).toContain('Total Dependencies')
  })

  it('shows docker issues count', () => {
    const deps = makeDeps({
      docker_issues: [{ file: 'Dockerfile', issue: 'no healthcheck' }],
    })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    expect(w.text()).toContain('1')
    expect(w.text()).toContain('Docker Issues')
  })
})

describe('DependenciesPanel — empty state', () => {
  it('shows empty state when no deps and no docker issues', () => {
    const w = mount(DependenciesPanel, { props: { deps: makeDeps() }, global: { stubs } })
    expect(w.find('.empty-state').exists()).toBe(true)
    expect(w.text()).toContain('No dependency files found')
  })

  it('hides empty state when deps present', () => {
    const deps = makeDeps({
      dependency_count: 1,
      dependencies: [{ name: 'axios', version_spec: '^1.0.0', source: 'npm' }],
    })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    expect(w.find('.empty-state').exists()).toBe(false)
  })
})

describe('DependenciesPanel — CVE banner', () => {
  it('shows CVE badge when vulnerabilities present', () => {
    const deps = makeDeps({
      dependency_count: 2,
      dependencies: [
        { name: 'lodash', version_spec: '4.17.15', source: 'npm' },
        { name: 'axios', version_spec: '0.21.0', source: 'npm' },
      ],
    })
    const security = makeSecurity({
      vulnerabilities: [
        { name: 'lodash', version: '4.17.15', ecosystem: 'npm', vuln_id: 'GHSA-1', summary: '', severity: 'high', url: 'https://osv.dev/vulnerability/GHSA-1' },
        { name: 'axios', version: '0.21.0', ecosystem: 'npm', vuln_id: 'GHSA-2', summary: '', severity: 'medium', url: 'https://osv.dev/vulnerability/GHSA-2' },
      ],
    })
    const w = mount(DependenciesPanel, { props: { deps, security }, global: { stubs } })
    expect(w.text()).toContain('2 CVEs found')
  })

  it('hides CVE banner when no vulnerabilities', () => {
    const deps = makeDeps({
      dependency_count: 1,
      dependencies: [{ name: 'vue', version_spec: '^3.0.0', source: 'npm' }],
    })
    const w = mount(DependenciesPanel, { props: { deps, security: makeSecurity() }, global: { stubs } })
    expect(w.find('.warning-row').exists()).toBe(false)
  })
})

describe('DependenciesPanel — dependency table', () => {
  it('renders a row per dependency', () => {
    // Use non-framework names — the table filters out KNOWN_FRAMEWORKS by default
    const deps = makeDeps({
      dependency_count: 2,
      dependencies: [
        { name: 'my-custom-lib', version_spec: '^1.0.0', source: 'npm' },
        { name: 'another-lib', version_spec: '^2.0.0', source: 'npm' },
      ],
    })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    const rows = w.findAll('tbody tr')
    expect(rows).toHaveLength(2)
  })

  it('marks vulnerable package with CVE badge in the table row', () => {
    const deps = makeDeps({
      dependency_count: 1,
      dependencies: [{ name: 'my-vuln-lib', version_spec: '1.0.0', source: 'npm' }],
    })
    const security = makeSecurity({ vulnerabilities: [{ name: 'my-vuln-lib', version: '1.0.0', ecosystem: 'npm', vuln_id: 'GHSA-3', summary: '', severity: 'high', url: 'https://osv.dev/vulnerability/GHSA-3' }] })
    const w = mount(DependenciesPanel, { props: { deps, security }, global: { stubs } })
    // findAll — first is the CVE banner, second is the inline row badge
    const failedBadges = w.findAll('[data-variant="failed"]')
    expect(failedBadges.length).toBeGreaterThanOrEqual(2)
    expect(failedBadges[failedBadges.length - 1].text()).toBe('CVE')
  })

  it('labels dev dependency correctly', () => {
    const deps = makeDeps({
      dependency_count: 1,
      dependencies: [{ name: 'my-dev-tool', version_spec: '^3.0.0', source: 'npm', dev: true }],
    })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    const infoBadge = w.find('[data-variant="info"]')
    expect(infoBadge.text()).toBe('dev')
  })

  it('labels prod dependency correctly', () => {
    const deps = makeDeps({
      dependency_count: 1,
      dependencies: [{ name: 'my-prod-lib', version_spec: '^3.0.0', source: 'npm', dev: false }],
    })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    const prodBadge = w.find('[data-variant="completed"]')
    expect(prodBadge.text()).toBe('prod')
  })
})

describe('DependenciesPanel — lockfile warnings', () => {
  it('renders lockfile warnings', () => {
    const deps = makeDeps({ missing_lockfile_warnings: ['No lockfile found for npm'] })
    const w = mount(DependenciesPanel, { props: { deps }, global: { stubs } })
    expect(w.text()).toContain('No lockfile found for npm')
  })
})
