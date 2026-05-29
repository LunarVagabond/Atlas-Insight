<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import AppTabs from '../components/ui/AppTabs.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'
import AnalysisStatusCard from '../components/analysis/AnalysisStatusCard.vue'
import OverviewPanel from '../components/analysis/OverviewPanel.vue'
import CommitTimelineChart from '../components/analysis/CommitTimelineChart.vue'
import ArchitecturePanel from '../components/analysis/ArchitecturePanel.vue'
import DependencyGraphView from '../components/analysis/DependencyGraphView.vue'
import DependenciesPanel from '../components/analysis/DependenciesPanel.vue'
import HeuristicsPanel from '../components/analysis/HeuristicsPanel.vue'

const route = useRoute()
const router = useRouter()
const store = useAnalysisStore()
const runId = Number(route.params.runId)

const TABS = ['Overview', 'Architecture', 'Dependencies', 'Timeline', 'Heuristics']
const activeTab = ref('Overview')

onMounted(async () => {
  if (!runId || isNaN(runId)) {
    router.push('/')
    return
  }
  await store.pollRun(runId)
})

onUnmounted(() => store._stopPolling())

const result = computed(() => store.run?.result)
const isPolling = computed(() => ['pending', 'running'].includes(store.run?.status ?? ''))
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <div class="results-header">
        <h1 class="results-header__title">Analysis Results</h1>
        <a href="/" class="btn btn--secondary" style="font-size:0.875rem">← New Analysis</a>
      </div>
      <div v-if="store.run" style="margin-top: 1rem">
        <AnalysisStatusCard :run="store.run" />
      </div>
    </div>

    <div v-if="isPolling" class="results-layout__content">
      <LoadingSpinner size="lg" label="Analysis in progress — this may take a minute..." />
    </div>

    <div v-else-if="store.status === 'error'" class="results-layout__content">
      <div class="empty-state">Analysis failed. {{ store.error }}</div>
    </div>

    <div v-else-if="result" class="results-layout__content">
      <AppTabs :tabs="TABS" v-model="activeTab" />
      <div style="margin-top: 1.5rem">
        <OverviewPanel v-if="activeTab === 'Overview'" :result="result" />
        <template v-if="activeTab === 'Architecture'">
          <ArchitecturePanel :graph="result.graph" />
          <div style="margin-top: 1.5rem">
            <DependencyGraphView :graph="result.graph" />
          </div>
        </template>
        <DependenciesPanel v-if="activeTab === 'Dependencies'" :deps="result.dependencies" />
        <CommitTimelineChart v-if="activeTab === 'Timeline'" :commits="result.commits" />
        <HeuristicsPanel v-if="activeTab === 'Heuristics'" :signals="result.heuristics" />
      </div>
    </div>
  </div>
</template>
