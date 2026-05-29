<script setup lang="ts">
import { ref } from 'vue'
import AppCard from '../ui/AppCard.vue'
import HeuristicDrawer from './HeuristicDrawer.vue'
import type { HeuristicSignal, HeuristicSignalKey } from '../../stores/analysis'

defineProps<{ signals: HeuristicSignal[] }>()

const active = ref<HeuristicSignal | null>(null)

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
  if (score < 30) return 'Low Risk'
  if (score < 60) return 'Moderate Risk'
  return 'High Risk'
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Heuristic Insights</h2>
    <div class="heuristics-grid">
      <AppCard
        v-for="signal in signals"
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
            <div class="heuristic__score-display">
              <span :class="['heuristic__score-number', `heuristic__score-number--${level(signal.score)}`]">
                {{ signal.score }}
              </span>
              <span class="heuristic__score-label">/ 100</span>
            </div>
          </div>

          <div class="heuristic__bar">
            <div
              :class="['heuristic__bar-fill', `heuristic__bar-fill--${level(signal.score)}`]"
              :style="{ width: `${signal.score}%` }"
            />
          </div>

          <div class="heuristic__footer">
            <span :class="['heuristic__confidence-dot', `heuristic__confidence-dot--${signal.confidence}`]" />
            <span class="heuristic__confidence-text">{{ signal.confidence }} confidence</span>
            <span class="heuristic__details-hint">Details →</span>
          </div>
        </div>
      </AppCard>
    </div>

    <HeuristicDrawer :signal="active" @close="active = null" />
  </div>
</template>
