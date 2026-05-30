<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import AppCard from '../components/ui/AppCard.vue'
import AppButton from '../components/ui/AppButton.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'

interface AdminStats {
  total_repos: number
  total_runs: number
  queue_depth: number
  failed_runs: number
  completed_runs: number
  repo_clone_count: number
  cache_size_gb: number
}

const stats = ref<AdminStats | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const accessDenied = ref(false)

async function fetchStats() {
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get<AdminStats>('/api/v1/repositories/admin/stats')
    stats.value = data
  } catch (err: any) {
    if (err?.response?.status === 403) {
      accessDenied.value = true
    } else {
      error.value = 'Failed to load admin stats'
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <h1 class="panel__title" style="font-size:1.5rem">Ops Dashboard</h1>
    </div>

    <div class="results-layout__content">
      <div v-if="accessDenied" class="empty-state">
        Staff access only.
      </div>

      <LoadingSpinner v-else-if="loading" label="Loading stats…" />

      <div v-else-if="error" class="empty-state">{{ error }}</div>

      <template v-else-if="stats">
        <div class="panel">
          <p class="panel__title">System Health</p>
          <div class="panel__grid">
            <AppCard>
              <div class="stat__value">{{ stats.total_repos }}</div>
              <div class="stat__label">Total Repos</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.total_runs }}</div>
              <div class="stat__label">Total Runs</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.queue_depth }}</div>
              <div class="stat__label">Queue Depth</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.failed_runs }}</div>
              <div class="stat__label">Failed Runs</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.completed_runs }}</div>
              <div class="stat__label">Completed Runs</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.repo_clone_count }}</div>
              <div class="stat__label">Cached Clones</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.cache_size_gb }} GB</div>
              <div class="stat__label">Cache Size</div>
            </AppCard>
          </div>
        </div>

        <div style="margin-top:1.5rem">
          <AppButton variant="secondary" :disabled="loading" @click="fetchStats">
            Refresh
          </AppButton>
        </div>
      </template>
    </div>
  </div>
</template>
