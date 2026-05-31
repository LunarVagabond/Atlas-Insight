<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import AppButton from '../ui/AppButton.vue'
import { useAnalysisStore } from '../../stores/analysis'
import type { AnalysisRun } from '../../stores/analysis'
import { techStackFromDeps } from '../../composables/frameworkSignals'

const props = defineProps<{ run: AnalysisRun }>()
const store = useAnalysisStore()
const router = useRouter()

const techStack = computed(() => {
  if (props.run.result?.structure?.tech_stack?.length) {
    return props.run.result.structure.tech_stack
  }
  const deps = props.run.result?.dependencies?.dependencies ?? []
  return techStackFromDeps(deps)
})

const ossScore = computed(() => props.run.result?.oss_score ?? null)

const ossBadgeEmoji: Record<string, string> = {
  champion: '🏆',
  thriving: '⭐',
  growing: '🌱',
  seedling: '🌿',
  struggling: '😬',
  dormant: '💀',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

async function reanalyze() {
  const newRunId = await store.retryRun(props.run.id)
  router.push(`/results/${newRunId}`)
}
</script>

<template>
  <AppCard>
    <div class="status-card">
      <div class="status-card__main-row">
        <div class="status-card__meta">
          <div class="status-card__row">
            <span class="status-card__label">Author</span>
            <span class="status-card__value">{{ run.repo_owner }}</span>
          </div>
          <div v-if="run.result?.github_meta?.license_spdx ?? run.result?.structure?.license_type" class="status-card__row">
            <span class="status-card__label">License</span>
            <span class="status-card__value">{{ run.result?.github_meta?.license_spdx ?? run.result?.structure?.license_type }}</span>
          </div>
          <div class="status-card__row">
            <span class="status-card__label">Status</span>
            <div style="display:flex;align-items:center;gap:6px">
              <AppBadge :variant="run.status">{{ run.status }}</AppBadge>
              <span v-if="run.status === 'running' || run.status === 'pending'" class="spinner" style="width:14px;height:14px;border-width:2px" />
            </div>
          </div>
          <div class="status-card__row">
            <span class="status-card__label">Triggered</span>
            <span class="status-card__value">{{ formatDate(run.triggered_at) }}</span>
          </div>
          <div v-if="run.completed_at" class="status-card__row">
            <span class="status-card__label">Completed</span>
            <span class="status-card__value">{{ formatDate(run.completed_at) }}</span>
          </div>
          <div class="status-card__row">
            <span class="status-card__label">Last Pulled</span>
            <span class="status-card__value">{{ run.last_fetched_at ? formatDate(run.last_fetched_at) : 'Never' }}</span>
          </div>
          <div v-if="techStack.length" class="status-card__stack">
            <AppBadge v-for="t in techStack" :key="t" variant="info">{{ t }}</AppBadge>
          </div>
          <div v-if="run.is_stale" class="status-card__row">
            <span class="status-card__label">Freshness</span>
            <div class="status-card__stale">
              <AppBadge variant="warning">Stale</AppBadge>
              <AppButton variant="secondary" @click="reanalyze">Refresh Project</AppButton>
            </div>
          </div>
        </div>

        <div v-if="ossScore" :class="['status-card__oss', `status-card__oss--${ossScore.badge}`]">
          <span class="status-card__oss-heading">OSS Score</span>
          <div class="status-card__oss-main">
            <span class="status-card__oss-emoji">{{ ossBadgeEmoji[ossScore.badge] }}</span>
            <span class="status-card__oss-divider">|</span>
            <span class="status-card__oss-score">{{ ossScore.score.toFixed(1) }}<span class="status-card__oss-of">/10</span></span>
          </div>
          <span class="status-card__oss-label">{{ ossScore.label }}</span>
        </div>
      </div>
    </div>
  </AppCard>
</template>
