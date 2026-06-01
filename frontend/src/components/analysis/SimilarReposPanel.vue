<script setup lang="ts">
import type { SimilarRun } from '../../stores/analysis'

defineProps<{
  runs: SimilarRun[]
  loading: boolean
}>()

const HEALTH_LABELS: Record<string, string> = {
  thriving: 'Thriving',
  active: 'Active',
  stable: 'Stable',
  declining: 'Declining',
  abandoned: 'Abandoned',
}
</script>

<template>
  <div class="similar-panel">
    <h3 class="similar-panel__title">Similar Repos</h3>

    <div v-if="loading" class="similar-panel__loading">
      <span class="spinner spinner--sm" />
      <span>Finding similar repos…</span>
    </div>

    <div v-else-if="!runs.length" class="similar-panel__empty">
      No similar repos in analyzed pool yet.
    </div>

    <div v-else class="similar-panel__grid">
      <RouterLink
        v-for="r in runs"
        :key="r.run_id"
        :to="`/results/${r.run_id}`"
        class="similar-card"
      >
        <div class="similar-card__header">
          <span class="similar-card__name">{{ r.owner }}/{{ r.name }}</span>
          <span class="similar-card__score">{{ r.oss_score.toFixed(1) }}</span>
        </div>
        <div class="similar-card__meta">
          <span v-if="r.primary_language" class="similar-card__lang">{{ r.primary_language }}</span>
          <span :class="['similar-card__health', `similar-card__health--${r.health_key}`]">
            {{ HEALTH_LABELS[r.health_key] ?? r.health_key }}
          </span>
          <span class="similar-card__stars">★ {{ r.stars.toLocaleString() }}</span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>
