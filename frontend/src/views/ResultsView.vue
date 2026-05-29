<script setup lang="ts">
import { ref, onUnmounted, computed, watch } from 'vue'
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
import ProjectPanel from '../components/analysis/ProjectPanel.vue'
import ContributingPanel from '../components/analysis/ContributingPanel.vue'
import RoadmapTimeline from '../components/analysis/RoadmapTimeline.vue'

const route = useRoute()
const router = useRouter()
const store = useAnalysisStore()
const runId = computed(() => route.params.runId as string)

const hasRoadmap = computed(() => (result.value?.structure?.roadmap_parsed?.milestones?.length ?? 0) > 0)
const TABS = computed(() => {
  const base = ['Overview', 'Project', 'Architecture', 'Dependencies', 'Timeline', 'Heuristics', 'Contributing']
  if (hasRoadmap.value) base.push('Roadmap')
  return base
})
const activeTab = ref('Overview')

watch(runId, async (id) => {
  if (!id) { router.push('/'); return }
  store._stopPolling()
  await store.pollRun(id)
}, { immediate: true })


onUnmounted(() => store._stopPolling())

const result = computed(() => store.run?.result)
const isPolling = computed(() => ['pending', 'running'].includes(store.run?.status ?? ''))
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <div class="results-header">
        <div style="display:flex;align-items:baseline;gap:0.75rem">
          <h1 class="results-header__title">Analysis Results</h1>
          <a v-if="store.run?.repo_url" :href="store.run.repo_url" target="_blank" rel="noopener noreferrer" class="results-header__repo-link">
            {{ store.run.repo_owner }}/{{ store.run.repo_name }} ↗
          </a>
        </div>
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
        <ProjectPanel v-if="activeTab === 'Project'" :result="result" />
        <template v-if="activeTab === 'Architecture'">
          <ArchitecturePanel :graph="result.graph" />
          <div style="margin-top: 1.5rem">
            <DependencyGraphView :graph="result.graph" />
          </div>
        </template>
        <DependenciesPanel v-if="activeTab === 'Dependencies'" :deps="result.dependencies" />
        <CommitTimelineChart v-if="activeTab === 'Timeline'" :commits="result.commits" />
        <HeuristicsPanel v-if="activeTab === 'Heuristics'" :signals="result.heuristics" />
        <ContributingPanel v-if="activeTab === 'Contributing'" :opportunities="result.contribution_opportunities ?? []" :repo-url="store.run?.repo_url" :structure="result.structure" />
        <div v-if="activeTab === 'Roadmap' && result.structure?.roadmap_parsed" class="panel">
          <RoadmapTimeline
            :milestones="result.structure.roadmap_parsed.milestones"
            :roadmap-file="result.structure.roadmap_file ?? 'ROADMAP.md'"
          />
        </div>
      </div>
    </div>
  </div>
</template>
