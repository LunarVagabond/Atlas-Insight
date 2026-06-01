<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import AppBadge from '../components/ui/AppBadge.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'

const router = useRouter()

interface TrendingRepo {
  run_id: string
  repo_url: string
  repo_owner: string
  repo_name: string
  analysis_count: number
  health_label: string | null
  health_key: string | null
  primary_language: string | null
  stars: number | null
}

type BadgeVariant = 'pending' | 'running' | 'completed' | 'failed' | 'warning' | 'info'
const HEALTH_COLORS: Record<string, BadgeVariant> = {
  thriving: 'completed',
  active: 'completed',
  stable: 'warning',
  declining: 'failed',
  abandoned: 'failed',
}

const items = ref<TrendingRepo[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/repositories/trending')
    items.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="trending-view">
    <div class="trending-view__header">
      <h1 class="trending-view__title">Trending This Week</h1>
      <p class="trending-view__subtitle">Most-analyzed repositories in the last 7 days.</p>
    </div>

    <LoadingSpinner v-if="loading" label="Loading…" />

    <div v-else-if="!items.length" class="empty-state" style="padding: 3rem 0; text-align:center">
      No trending data yet — check back after some repos have been analyzed.
    </div>

    <div v-else class="trending-view__grid">
      <div
        v-for="(repo, i) in items"
        :key="repo.run_id"
        class="trending-view__card"
        @click="router.push(`/results/${repo.run_id}`)"
      >
        <div class="trending-view__rank">#{{ i + 1 }}</div>
        <div class="trending-view__info">
          <div class="trending-view__name">
            <span class="trending-view__owner">{{ repo.repo_owner }}</span>
            <span class="trending-view__sep">/</span>
            <span class="trending-view__repo">{{ repo.repo_name }}</span>
          </div>
          <div class="trending-view__meta">
            <span v-if="repo.primary_language" class="trending-view__lang">{{ repo.primary_language }}</span>
            <span v-if="repo.stars !== null" class="trending-view__stars">★ {{ repo.stars?.toLocaleString() }}</span>
            <span class="trending-view__count">{{ repo.analysis_count }}× analyzed</span>
          </div>
        </div>
        <div class="trending-view__badge">
          <AppBadge
            v-if="repo.health_label && repo.health_key"
            :variant="(HEALTH_COLORS[repo.health_key] ?? 'info') as BadgeVariant"
          >{{ repo.health_label }}</AppBadge>
        </div>
      </div>
    </div>
  </div>
</template>
