<script setup lang="ts">
import { computed, ref } from 'vue'
import AppCard from '../ui/AppCard.vue'
import HeuristicDrawer from './HeuristicDrawer.vue'
import SubProjectSelector from './SubProjectSelector.vue'
import type { HeuristicSignal, HeuristicSignalKey, RunResult, SubProject } from '../../stores/analysis'

const props = defineProps<{
  signals: HeuristicSignal[]
  result?: RunResult
  subProjects?: SubProject[]
  selectedSubProject?: string | null
}>()

const emit = defineEmits<{ 'update:selectedSubProject': [name: string | null] }>()

const activeSignals = computed<HeuristicSignal[]>(() => {
  const raw = (!props.selectedSubProject || !props.subProjects?.length)
    ? props.signals
    : (props.subProjects.find(sp => sp.name === props.selectedSubProject)?.heuristics ?? props.signals)
  return [...raw].sort((a, b) => (SIGNAL_ORDER[a.signal] ?? 99) - (SIGNAL_ORDER[b.signal] ?? 99))
})

const active = ref<HeuristicSignal | null>(null)
const activeHint = ref<HeuristicSignalKey | null>(null)

function toggleHint(e: Event, key: HeuristicSignalKey) {
  e.stopPropagation()
  activeHint.value = activeHint.value === key ? null : key
}

const SIGNAL_ICONS: Record<HeuristicSignalKey, string> = {
  burnout:               '🔥',
  abandonment_risk:      '💤',
  monolith_growth:       '🏗️',
  dependency_health:     '📦',
  documentation_quality: '📝',
  ci_health:             '⚙️',
  bus_factor_risk:       '🚌',
  security_hygiene:      '🔒',
  release_cadence:       '🏷️',
  community_health:      '🤝',
  commit_velocity:       '📈',
  license_risk:          '⚖️',
  complexity_debt:       '🧩',
  test_coverage:         '🧪',
  cicd_maturity:         '🚀',
  container_hygiene:     '🐳',
}

const SIGNAL_ORDER: Record<HeuristicSignalKey, number> = {
  // Activity & Health
  burnout: 0, abandonment_risk: 1, commit_velocity: 2,
  // Code Structure
  monolith_growth: 10, complexity_debt: 11,
  // Testing & CI (grouped together)
  test_coverage: 20, ci_health: 21, cicd_maturity: 22,
  // Dependencies & Security
  dependency_health: 30, security_hygiene: 31, license_risk: 32, container_hygiene: 33,
  // Community & Docs
  documentation_quality: 40, community_health: 41, release_cadence: 42, bus_factor_risk: 43,
}

function icon(signal: HeuristicSignalKey): string {
  return SIGNAL_ICONS[signal] ?? '📊'
}

function level(score: number): 'low' | 'medium' | 'high' {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

function riskLabel(score: number): string {
  if (score < 30) return 'Low concern'
  if (score < 60) return 'Worth watching'
  return 'Needs attention'
}

// Composite health score — uses backend oss_score (weighted, 0-10 → scaled to 0-100).
// Falls back to inverting the unweighted average risk score if oss_score is unavailable.
// Individual signal scores are risk scores (0=good, 100=bad), so the composite inverts
// them so the display reads as a health/quality score (higher = better).
const overallScore = computed(() => {
  if (!activeSignals.value.length) return null
  const oss = props.result?.oss_score
  if (oss != null) return Math.round(oss.score * 10)
  const total = activeSignals.value.reduce((sum, s) => sum + s.score, 0)
  return Math.round(100 - total / activeSignals.value.length)
})

const ossLabel = computed(() => props.result?.oss_score?.label ?? null)

const isClosedSource = computed(
  () => (props.result?.scoring_mode ?? props.result?.oss_score?.mode) === 'closed_source',
)

const scoringModeBanner = computed(() => {
  if (!isClosedSource.value) return null
  const reason = props.result?.scoring_mode_reason
  return reason
    ? `Scored for closed-source context (${reason}) — community file expectations adjusted`
    : 'Scored for closed-source context — community file expectations adjusted'
})

function compositeLevel(score: number): 'low' | 'medium' | 'high' {
  if (score >= 70) return 'low'
  if (score >= 40) return 'medium'
  return 'high'
}

const scoreBreakdown = computed(() =>
  [...activeSignals.value]
    .sort((a, b) => b.score - a.score)
    .map(s => ({
      label: s.label,
      score: s.score,
      pct: s.score, // each signal is 0–100; bar width = score
      level: level(s.score),
    }))
)

const SIGNAL_DESCRIPTIONS: Partial<Record<HeuristicSignalKey, string>> = {
  burnout:               'Is one person doing most of the work? High scores mean too much depends on a single contributor.',
  abandonment_risk:      'How likely is it that this project is no longer being actively maintained.',
  monolith_growth:       'Is the codebase growing without clear structure? High scores mean it may be getting harder to navigate.',
  dependency_health:     'Are the project\'s libraries up to date and actively maintained by their authors?',
  documentation_quality: 'How well-documented is the project? Good docs help new contributors get started faster.',
  ci_health:             'Does the project use automated testing and deployment pipelines? These catch bugs before they ship.',
  bus_factor_risk:       'How many contributors could leave before the project loses critical knowledge?',
  security_hygiene:      'Are common security practices in place — like a security policy, .gitignore, and avoiding hardcoded secrets?',
  release_cadence:       'How regularly does the project ship new versions? Consistent releases signal a healthy project.',
  community_health:      'Does the project have the community files that make it easier for others to contribute and participate?',
  commit_velocity:       'Is code being committed regularly? Slowing velocity can signal a project winding down.',
  license_risk:          'Does the project have a clear open source license? Without one the code is legally all-rights-reserved.',
  complexity_debt:       'Are there large, hard-to-maintain files in the codebase? High scores mean growing complexity risk.',
  test_coverage:         'How much of the codebase has test files? Untested directories are blind spots for regressions.',
  cicd_maturity:         'Does the CI pipeline go beyond just building — does it run tests and lint on every change?',
  container_hygiene:     'Are the Dockerfiles following security best practices — avoiding root, pinning base images?',
}

const improvementHints = computed<string[]>(() => {
  if (!activeSignals.value.length) return []
  const hints: string[] = []
  for (const s of [...activeSignals.value].sort((a, b) => b.score - a.score)) {
    if (s.score < 40) continue
    switch (s.signal) {
      case 'community_health':
        if (isClosedSource.value) break
        if (s.items?.some(i => i.toLowerCase().includes('license'))) hints.push('Add a LICENSE file — without one the code is all-rights-reserved')
        else if (s.items?.some(i => i.toLowerCase().includes('contributing'))) hints.push('Add a CONTRIBUTING.md to help new contributors')
        else hints.push('Add missing community health files (LICENSE, CONTRIBUTING, SECURITY)')
        break
      case 'license_risk':
        if (!isClosedSource.value) hints.push('Add or clarify the repository license to enable legal reuse')
        break
      case 'ci_health':
        hints.push('Set up CI automation (e.g. GitHub Actions) with automated tests on every push')
        break
      case 'cicd_maturity':
        hints.push('Add test and lint steps to the existing CI pipeline')
        break
      case 'test_coverage':
        hints.push('Add test files to directories that currently have none')
        break
      case 'documentation_quality':
        hints.push('Expand the README with installation and usage instructions')
        break
      case 'security_hygiene':
        hints.push('Review .gitignore coverage and rotate any accidentally committed secrets')
        break
      case 'container_hygiene':
        hints.push('Pin base image tags and add a non-root USER to Dockerfiles')
        break
      case 'complexity_debt':
        hints.push('Refactor the largest files into smaller, focused modules')
        break
      case 'dependency_health':
        hints.push('Update deprecated Docker base images and add missing lockfiles')
        break
      case 'release_cadence':
        hints.push('Start tagging releases so users have a clear update path')
        break
    }
    if (hints.length >= 3) break
  }
  return hints
})
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Health Signals</h2>
    <p class="panel__subtitle">Automated signals about this project's activity, health, and contributor patterns — click any card for details.</p>

    <p v-if="scoringModeBanner" class="panel__hint">{{ scoringModeBanner }}</p>

    <SubProjectSelector
      v-if="subProjects?.length"
      :sub-projects="subProjects"
      :model-value="selectedSubProject ?? null"
      style="margin-bottom: 1rem"
      @update:model-value="emit('update:selectedSubProject', $event)"
    />

    <p v-if="selectedSubProject && activeSignals.length < 11" class="panel__hint">
      Repo-wide signals (Documentation, CI Health, Community Health, Release Cadence, Bus Factor) are omitted in sub-project view.
    </p>

    <!-- Score Breakdown -->
    <div v-if="overallScore !== null" class="score-breakdown">
      <h4 class="score-breakdown__heading">At a Glance</h4>
      <div class="score-breakdown__body">
        <div class="score-breakdown__summary">
          <span class="score-breakdown__title">
            Health Score<span v-if="ossLabel" class="score-breakdown__badge"> · {{ ossLabel }}</span>
          </span>
          <span :class="['score-breakdown__total', `score-breakdown__total--${compositeLevel(overallScore)}`]">
            {{ overallScore }}<span class="score-breakdown__denom">/100</span>
          </span>
        </div>
        <div class="score-breakdown__bars">
          <div v-for="item in scoreBreakdown" :key="item.label" class="score-breakdown__row">
            <span class="score-breakdown__label">
              {{ item.label }}
              <span :class="['score-breakdown__val', `score-breakdown__val--${item.level}`]">({{ item.score }})</span>
            </span>
            <div class="score-breakdown__track">
              <div
                :class="['score-breakdown__fill', `score-breakdown__fill--${item.level}`]"
                :style="{ width: `${item.pct}%` }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Improvement hints -->
    <div v-if="improvementHints.length" class="improvement-hints">
      <p class="improvement-hints__heading">Ways to improve this score</p>
      <ul class="improvement-hints__list">
        <li v-for="(hint, i) in improvementHints" :key="i">{{ hint }}</li>
      </ul>
    </div>

    <div class="heuristics-grid">
      <AppCard
        v-for="signal in activeSignals"
        :key="signal.signal"
        elevated
        :class="['heuristic-card', `heuristic-card--${level(signal.score)}`, 'heuristic-card--clickable']"
        @click="active = signal"
      >
        <div class="heuristic">
          <div class="heuristic__top">
            <div class="heuristic__title-group">
              <div class="heuristic__icon-label">
                <span class="heuristic__icon">{{ icon(signal.signal) }}</span>
                <span class="heuristic__label">{{ signal.label }}</span>
              </div>
              <span :class="['heuristic__risk', `heuristic__risk--${level(signal.score)}`]">
                {{ riskLabel(signal.score) }}
              </span>
            </div>
            <div style="display:flex;align-items:center;gap:0.5rem">
              <div class="heuristic__score-display">
                <span :class="['heuristic__score-number', `heuristic__score-number--${level(signal.score)}`]">
                  {{ signal.score }}
                </span>
                <span class="heuristic__score-label">/ 100</span>
              </div>
              <button
                v-if="SIGNAL_DESCRIPTIONS[signal.signal]"
                class="card-hint-btn"
                :class="{ 'card-hint-btn--active': activeHint === signal.signal }"
                :aria-label="`What does ${signal.label} mean?`"
                @click="toggleHint($event, signal.signal)"
              >?</button>
            </div>
          </div>

          <Transition name="hint-expand">
            <p v-if="activeHint === signal.signal && SIGNAL_DESCRIPTIONS[signal.signal]" class="card-hint-text">
              {{ SIGNAL_DESCRIPTIONS[signal.signal] }}
            </p>
          </Transition>

          <div class="heuristic__bar">
            <div
              :class="['heuristic__bar-fill', `heuristic__bar-fill--${level(signal.score)}`]"
              :style="{ width: `${signal.score}%` }"
            />
          </div>

          <div class="heuristic__footer">
            <span :class="['heuristic__confidence-dot', `heuristic__confidence-dot--${signal.confidence}`]" />
            <span class="heuristic__confidence-text" :title="signal.confidence === 'high' ? 'Strong data signal' : signal.confidence === 'medium' ? 'Moderate data signal' : 'Limited data available'">{{ signal.confidence }} confidence</span>
            <span class="heuristic__details-hint">Details →</span>
          </div>
        </div>
      </AppCard>
    </div>

    <HeuristicDrawer :signal="active" :result="result" @close="active = null" />
  </div>
</template>
