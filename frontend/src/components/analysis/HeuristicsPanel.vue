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
  if (!props.selectedSubProject || !props.subProjects?.length) return props.signals
  return props.subProjects.find(sp => sp.name === props.selectedSubProject)?.heuristics ?? props.signals
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

// Weighted score breakdown
const overallScore = computed(() => {
  if (!activeSignals.value.length) return null
  const total = activeSignals.value.reduce((sum, s) => sum + s.score, 0)
  return Math.round(total / activeSignals.value.length)
})

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
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Health Signals</h2>
    <p class="panel__subtitle">Automated signals about this project's activity, health, and contributor patterns — click any card for details.</p>

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
      <div class="score-breakdown__body">
        <div class="score-breakdown__summary">
          <span class="score-breakdown__title">Composite Score</span>
          <span :class="['score-breakdown__total', `score-breakdown__total--${level(overallScore)}`]">
            {{ overallScore }}<span class="score-breakdown__denom">/100</span>
          </span>
        </div>
        <div class="score-breakdown__bars">
          <div v-for="item in scoreBreakdown" :key="item.label" class="score-breakdown__row">
            <span class="score-breakdown__label">{{ item.label }}</span>
            <div class="score-breakdown__track">
              <div
                :class="['score-breakdown__fill', `score-breakdown__fill--${item.level}`]"
                :style="{ width: `${item.pct}%` }"
              />
            </div>
            <span :class="['score-breakdown__val', `score-breakdown__val--${item.level}`]">{{ item.score }}</span>
          </div>
        </div>
      </div>
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
