import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HeuristicsPanel from '../components/analysis/HeuristicsPanel.vue'
import type { HeuristicSignal } from '../types/heuristics'
import type { RunResult } from '../types/run'

// Minimal stubs for complex child components
const stubs = {
  AppCard: { template: '<div><slot /></div>' },
  AppTabs: { template: '<div />' },
  HeuristicDrawer: { template: '<div />' },
  SubProjectSelector: { template: '<div />' },
}

function makeSignal(signal: string, score: number): HeuristicSignal {
  return {
    signal: signal as HeuristicSignal['signal'],
    label: signal,
    score,
    confidence: 'high',
    description: '',
  }
}

describe('HeuristicsPanel — composite health score', () => {
  it('uses oss_score * 10 when available', () => {
    const signals = [makeSignal('burnout', 80), makeSignal('abandonment_risk', 70)]
    const result = { oss_score: { score: 7.5, badge: 'thriving', label: 'Thriving' } } as Partial<RunResult>

    const wrapper = mount(HeuristicsPanel, {
      props: { signals, result: result as RunResult },
      global: { stubs },
    })

    // 7.5 * 10 = 75
    expect(wrapper.find('.score-breakdown__total').text()).toContain('75')
  })

  it('falls back to 100 - avg_risk when oss_score absent', () => {
    // scores 40 + 60 → avg = 50 → health = 50
    const signals = [makeSignal('burnout', 40), makeSignal('abandonment_risk', 60)]

    const wrapper = mount(HeuristicsPanel, {
      props: { signals },
      global: { stubs },
    })

    expect(wrapper.find('.score-breakdown__total').text()).toContain('50')
  })

  it('hides score breakdown when no signals', () => {
    const wrapper = mount(HeuristicsPanel, {
      props: { signals: [] },
      global: { stubs },
    })

    expect(wrapper.find('.score-breakdown').exists()).toBe(false)
  })

  it('shows oss label badge when oss_score present', () => {
    const signals = [makeSignal('burnout', 20)]
    const result = { oss_score: { score: 8, badge: 'champion', label: 'Champion' } } as Partial<RunResult>

    const wrapper = mount(HeuristicsPanel, {
      props: { signals, result: result as RunResult },
      global: { stubs },
    })

    expect(wrapper.find('.score-breakdown__badge').text()).toContain('Champion')
  })

  it('hides label badge when no oss_score', () => {
    const signals = [makeSignal('burnout', 50)]

    const wrapper = mount(HeuristicsPanel, {
      props: { signals },
      global: { stubs },
    })

    expect(wrapper.find('.score-breakdown__badge').exists()).toBe(false)
  })

  it('score ≥ 70 gets --low class (green/healthy)', () => {
    const signals = [makeSignal('burnout', 5)]
    const result = { oss_score: { score: 8, badge: 'thriving', label: 'Thriving' } } as Partial<RunResult>

    const wrapper = mount(HeuristicsPanel, {
      props: { signals, result: result as RunResult },
      global: { stubs },
    })

    // 8 * 10 = 80 → compositeLevel → 'low' → --low suffix
    expect(wrapper.find('.score-breakdown__total--low').exists()).toBe(true)
  })

  it('score < 40 gets --high class (red/poor)', () => {
    const signals = [makeSignal('burnout', 5)]
    const result = { oss_score: { score: 3, badge: 'struggling', label: 'Struggling' } } as Partial<RunResult>

    const wrapper = mount(HeuristicsPanel, {
      props: { signals, result: result as RunResult },
      global: { stubs },
    })

    // 3 * 10 = 30 → compositeLevel → 'high' → --high suffix
    expect(wrapper.find('.score-breakdown__total--high').exists()).toBe(true)
  })
})

describe('HeuristicsPanel — individual signal cards', () => {
  it('renders one card per signal', () => {
    const signals = [
      makeSignal('burnout', 20),
      makeSignal('abandonment_risk', 50),
      makeSignal('ci_health', 80),
    ]

    const wrapper = mount(HeuristicsPanel, {
      props: { signals, section: 'Signals' },
      global: { stubs },
    })

    expect(wrapper.findAll('.heuristic-card')).toHaveLength(3)
  })

  it('applies correct risk class based on score', () => {
    const signals = [
      makeSignal('burnout', 15),       // < 30 → --low
      makeSignal('ci_health', 45),     // 30-60 → --medium
      makeSignal('security_hygiene', 75), // ≥ 60 → --high
    ]

    const wrapper = mount(HeuristicsPanel, {
      props: { signals, section: 'Signals' },
      global: { stubs },
    })

    const cards = wrapper.findAll('.heuristic-card')
    expect(cards[0].classes()).toContain('heuristic-card--low')
    expect(cards[1].classes()).toContain('heuristic-card--medium')
    expect(cards[2].classes()).toContain('heuristic-card--high')
  })
})
