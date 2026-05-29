<script setup lang="ts">
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { HeuristicSignal } from '../../stores/analysis'

defineProps<{ signals: HeuristicSignal[] }>()

function scoreLevel(score: number): 'low' | 'medium' | 'high' {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

function scoreBadgeVariant(score: number): 'completed' | 'warning' | 'failed' {
  if (score < 30) return 'completed'
  if (score < 60) return 'warning'
  return 'failed'
}

function confidenceBadgeVariant(conf: string): 'completed' | 'info' | 'warning' {
  if (conf === 'high') return 'completed'
  if (conf === 'medium') return 'info'
  return 'warning'
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Heuristic Insights</h2>
    <div class="heuristics-grid">
      <AppCard v-for="signal in signals" :key="signal.signal" elevated>
        <div class="heuristic">
          <div class="heuristic__header">
            <span class="heuristic__label">{{ signal.label }}</span>
            <div class="heuristic__badges">
              <AppBadge :variant="confidenceBadgeVariant(signal.confidence)">
                {{ signal.confidence }} confidence
              </AppBadge>
              <AppBadge :variant="scoreBadgeVariant(signal.score)">
                {{ signal.score }}/100
              </AppBadge>
            </div>
          </div>
          <div class="score-bar">
            <div
              class="score-bar__fill"
              :class="`score-bar__fill--${scoreLevel(signal.score)}`"
              :style="{ width: `${signal.score}%` }"
            />
          </div>
          <p class="heuristic__description">{{ signal.description }}</p>
        </div>
      </AppCard>
    </div>
  </div>
</template>
