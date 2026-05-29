<script setup lang="ts">
import { ref, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import AppTabs from '../components/ui/AppTabs.vue'
import AppButton from '../components/ui/AppButton.vue'
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
const result = computed(() => store.run?.result)
const isPolling = computed(() => ['pending', 'running'].includes(store.run?.status ?? ''))
const isInitialLoading = computed(() => store.status === 'polling' && !store.run)
const showProgress = computed(() => isInitialLoading.value || isPolling.value)

const ANALYSIS_STEPS = [
  'Connecting to GitHub…',
  'Cloning repository…',
  'Scanning file structure…',
  'Parsing dependencies…',
  'Analyzing commit history…',
  'Computing heuristics…',
  'Building dependency graph…',
  'Finalizing results…',
]
const currentStep = ref(0)
let stepTimer: ReturnType<typeof setInterval> | null = null

watch(isPolling, (polling) => {
  if (polling) {
    currentStep.value = 0
    stepTimer = setInterval(() => {
      if (currentStep.value < ANALYSIS_STEPS.length - 1) currentStep.value++
    }, 8000)
  } else {
    if (stepTimer) { clearInterval(stepTimer); stepTimer = null }
  }
}, { immediate: true })

const hasRoadmap = computed(() => (result.value?.structure?.roadmap_parsed?.milestones?.length ?? 0) > 0)
const TABS = computed(() => {
  const base = ['Overview', 'Project', 'Architecture', 'Dependencies', 'Timeline', 'Heuristics', 'Contributing']
  if (hasRoadmap.value) base.push('Roadmap')
  return base
})

const activeTab = ref((route.query.tab as string) || 'Overview')

watch(activeTab, (tab) => {
  router.replace({ query: { ...route.query, tab } })
})

watch(TABS, (tabs) => {
  if (!tabs.includes(activeTab.value)) activeTab.value = 'Overview'
})

watch(runId, async (id) => {
  if (!id) { router.push('/'); return }
  activeTab.value = (route.query.tab as string) || 'Overview'
  store._stopPolling()
  await store.pollRun(id)
}, { immediate: true })

onUnmounted(() => {
  store._stopPolling()
  if (stepTimer) { clearInterval(stepTimer); stepTimer = null }
})

// Re-analyze
const reanalyzing = ref(false)
async function reanalyze() {
  if (!runId.value) return
  reanalyzing.value = true
  try {
    const newId = await store.retryRun(runId.value)
    router.push(`/results/${newId}`)
  } finally {
    reanalyzing.value = false
  }
}

// Export JSON
function exportJson() {
  if (!result.value || !store.run) return
  const blob = new Blob([JSON.stringify(result.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.run.repo_owner}-${store.run.repo_name}-analysis.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Copy permalink
const copied = ref(false)
function copyLink() {
  const url = `${window.location.origin}/r/${store.run?.repo_owner}/${store.run?.repo_name}`
  navigator.clipboard.writeText(url)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
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
        <div class="results-header__actions">
          <AppButton v-if="result" variant="secondary" @click="copyLink" style="font-size:0.8125rem;padding:4px 12px">
            {{ copied ? '✓ Copied' : '🔗 Share' }}
          </AppButton>
          <AppButton v-if="result" variant="secondary" @click="exportJson" style="font-size:0.8125rem;padding:4px 12px">
            ↓ Export JSON
          </AppButton>
          <AppButton v-if="store.run?.status === 'completed'" variant="secondary" :disabled="reanalyzing" @click="reanalyze" style="font-size:0.8125rem;padding:4px 12px">
            {{ reanalyzing ? 'Queuing…' : '↻ Re-analyze' }}
          </AppButton>
          <a href="/" class="btn btn--secondary" style="font-size:0.875rem">← New Analysis</a>
        </div>
      </div>
      <div v-if="store.run" style="margin-top: 1rem">
        <AnalysisStatusCard :run="store.run" />
      </div>
    </div>

    <div v-if="showProgress" class="results-layout__content">
      <div class="analysis-progress">
        <div class="spinner spinner--xl" />
        <p class="analysis-progress__step">
          {{ isInitialLoading ? 'Loading analysis…' : ANALYSIS_STEPS[currentStep] }}
        </p>
        <p class="analysis-progress__hint">Typical analyses take 30–90 seconds.</p>
        <div v-if="isPolling" class="analysis-progress__track">
          <span
            v-for="(_, i) in ANALYSIS_STEPS"
            :key="i"
            :class="['analysis-progress__dot', i === currentStep && 'analysis-progress__dot--active', i < currentStep && 'analysis-progress__dot--done']"
          />
        </div>
      </div>
    </div>

    <div v-if="!showProgress && store.status === 'error'" class="results-layout__content">
      <div class="empty-state">Analysis failed. {{ store.error }}</div>
    </div>

    <Transition name="fade">
    <div v-if="!showProgress && result" class="results-layout__content">
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
    </Transition>
  </div>
</template>
