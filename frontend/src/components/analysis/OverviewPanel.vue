<script setup lang="ts">
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{ result: RunResult }>()

const { commits, heuristics } = props.result

const overallScore = Math.round(heuristics.reduce((acc, h) => acc + h.score, 0) / (heuristics.length || 1))

function scoreVariant(score: number): 'completed' | 'warning' | 'failed' {
  if (score < 30) return 'completed'
  if (score < 60) return 'warning'
  return 'failed'
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Overview</h2>
    <div class="panel__grid">
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ commits.total_commits.toLocaleString() }}</div>
          <div class="stat__label">Total Commits</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ commits.total_contributors }}</div>
          <div class="stat__label">Contributors</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ commits.days_since_last_commit ?? '—' }}</div>
          <div class="stat__label">Days Since Last Commit</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">
            <AppBadge :variant="scoreVariant(overallScore)">Risk: {{ overallScore }}/100</AppBadge>
          </div>
          <div class="stat__label">Overall Health Score</div>
        </div>
      </AppCard>
    </div>
    <div v-if="commits.abandoned" style="margin-top: 1rem">
      <AppBadge variant="failed">Repository appears abandoned (no commits in 365+ days)</AppBadge>
    </div>
  </div>
</template>
