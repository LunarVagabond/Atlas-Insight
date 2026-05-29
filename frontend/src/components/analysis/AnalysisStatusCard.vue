<script setup lang="ts">
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { AnalysisRun } from '../../stores/analysis'

defineProps<{ run: AnalysisRun }>()

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <AppCard>
    <div class="status-card">
      <div class="status-card__row">
        <span class="status-card__label">Status</span>
        <AppBadge :variant="run.status">{{ run.status }}</AppBadge>
      </div>
      <div class="status-card__row">
        <span class="status-card__label">Triggered</span>
        <span class="status-card__value">{{ formatDate(run.triggered_at) }}</span>
      </div>
      <div v-if="run.completed_at" class="status-card__row">
        <span class="status-card__label">Completed</span>
        <span class="status-card__value">{{ formatDate(run.completed_at) }}</span>
      </div>
      <div v-if="run.repo_url" class="status-card__row">
        <span class="status-card__label">Repository</span>
        <a :href="run.repo_url" target="_blank" rel="noopener noreferrer" class="status-card__link">
          {{ run.repo_owner }}/{{ run.repo_name }} ↗
        </a>
      </div>
    </div>
  </AppCard>
</template>
