<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import type { AnalysisRun } from '../stores/analysis'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'
import ComparePanel from '../components/analysis/ComparePanel.vue'

const route = useRoute()
const runA = ref<AnalysisRun | null>(null)
const runB = ref<AnalysisRun | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  const { a, b } = route.query
  if (!a || !b) {
    error.value = 'Two run IDs required (?a=...&b=...)'
    loading.value = false
    return
  }
  try {
    const [ra, rb] = await Promise.all([
      axios.get(`/api/v1/repositories/runs/${a}`),
      axios.get(`/api/v1/repositories/runs/${b}`),
    ])
    runA.value = ra.data
    runB.value = rb.data
  } catch {
    error.value = 'Failed to load one or both runs'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <div class="results-header">
        <h1 class="results-header__title">Repository Comparison</h1>
        <RouterLink to="/runs" class="btn btn--secondary" style="font-size:0.875rem">
          ← All Runs
        </RouterLink>
      </div>
    </div>
    <div class="results-layout__content">
      <LoadingSpinner v-if="loading" label="Loading runs…" />
      <div v-else-if="error" class="empty-state">{{ error }}</div>
      <ComparePanel v-else-if="runA && runB" :run-a="runA" :run-b="runB" />
    </div>
  </div>
</template>
