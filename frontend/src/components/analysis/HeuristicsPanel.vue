<script setup lang="ts">
import AppCard from '../ui/AppCard.vue'
import type { HeuristicSignal } from '../../stores/analysis'

defineProps<{ signals: HeuristicSignal[] }>()

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
        :class="['heuristic-card', `heuristic-card--${level(signal.score)}`]"
      >
        <div class="heuristic">
          <div class="heuristic__top">
            <div class="heuristic__title-group">
              <span class="heuristic__label">{{ signal.label }}</span>
              <span :class="['heuristic__risk', `heuristic__risk--${level(signal.score)}`]">
                {{ riskLabel(signal.score) }}
              </span>
            </div>
            <div class="heuristic__score-display">
              <span :class="['heuristic__score-number', `heuristic__score-number--${level(signal.score)}`]">
                {{ signal.score }}
              </span>
              <span class="heuristic__score-label">out of 100</span>
            </div>
          </div>

          <div class="heuristic__bar">
            <div
              :class="['heuristic__bar-fill', `heuristic__bar-fill--${level(signal.score)}`]"
              :style="{ width: `${signal.score}%` }"
            />
          </div>

          <p class="heuristic__description">{{ signal.description }}</p>

          <div class="heuristic__footer">
            <span :class="['heuristic__confidence-dot', `heuristic__confidence-dot--${signal.confidence}`]" />
            <span class="heuristic__confidence-text">{{ signal.confidence }} confidence</span>
          </div>
        </div>
      </AppCard>
    </div>
  </div>
</template>
