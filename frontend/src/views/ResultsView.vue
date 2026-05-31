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
import SecurityPanel from '../components/analysis/SecurityPanel.vue'
import ArchitectureToursPanel from '../components/analysis/ArchitectureToursPanel.vue'
import OwnershipPanel from '../components/analysis/OwnershipPanel.vue'

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
const TABS = computed(() => ['Overview', 'Project', 'Architecture', 'Tours', 'Ownership', 'Dependencies', 'Security', 'History', 'Heuristics', 'Contributing'])

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
  store.jitIssues = null
  store.jitPrs = null
  await store.pollRun(id)
}, { immediate: true })

watch(() => store.run?.status, (status) => {
  if (status === 'completed' && runId.value) {
    store.fetchJitData(runId.value)
  }
})

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

    <div v-if="store.status === 'error' && !result" class="results-layout__content">
      <div class="analysis-error-card">
        <div class="analysis-error-card__icon">✕</div>
        <h2 class="analysis-error-card__title">Analysis Failed</h2>
        <p class="analysis-error-card__message">{{ store.error }}</p>
        <div class="analysis-error-card__pat-hint">
          <p>This repository may require a Personal Access Token. Go back and use the PAT option when submitting.</p>
        </div>
        <div class="analysis-error-card__actions">
          <a href="/" class="btn btn--primary">← New Analysis</a>
        </div>
      </div>
    </div>

    <Transition name="fade">
    <div v-if="result" class="results-layout__content">
      <div v-if="store.status === 'error'" class="analysis-inline-error">
        <span class="analysis-inline-error__icon">✕</span>
        {{ store.error || 'Re-analysis failed.' }}
      </div>
      <div v-if="store.run?.auth_token_warning" class="analysis-token-warning">
        {{ store.run.auth_token_warning }}
      </div>
      <AppTabs :tabs="TABS" v-model="activeTab" />
      <div style="margin-top: 1.5rem">
        <OverviewPanel v-if="activeTab === 'Overview'" :result="result" />
        <ProjectPanel v-if="activeTab === 'Project'" :result="result" />
        <template v-if="activeTab === 'Architecture'">
          <ArchitecturePanel :graph="result.graph" :hot-files="result.structure?.hot_files" :structure="result.structure" />
          <div style="margin-top: 1.5rem">
            <DependencyGraphView :graph="result.graph" />
          </div>
        </template>
        <ArchitectureToursPanel v-if="activeTab === 'Tours'" :tours="result.arch_tours ?? []" :repo-url="store.run?.repo_url" />
        <OwnershipPanel
          v-if="activeTab === 'Ownership'"
          :ownership="result.ownership ?? { subsystems: [], top_contributors: [], bus_factor: 0 }"
          :jit-issues="store.jitIssues"
          :jit-loading="store.jitLoading"
          :repo-url="store.run?.repo_url"
          :github-contributors="result.github_meta?.contributors"
        />
        <DependenciesPanel v-if="activeTab === 'Dependencies'" :deps="result.dependencies" />
        <SecurityPanel v-if="activeTab === 'Security'" :security="result.security" :heuristics="result.heuristics" :structure="result.structure" />
        <template v-if="activeTab === 'History'">
          <CommitTimelineChart :commits="result.commits" :repo-url="store.run?.repo_url" />
          <div v-if="hasRoadmap && result.structure?.roadmap_parsed" style="margin-top: 1.5rem" class="panel">
            <RoadmapTimeline
              :milestones="result.structure.roadmap_parsed.milestones"
              :roadmap-file="result.structure.roadmap_file ?? 'ROADMAP.md'"
            />
          </div>
        </template>
        <HeuristicsPanel v-if="activeTab === 'Heuristics'" :signals="result.heuristics" />
        <ContributingPanel v-if="activeTab === 'Contributing'" :opportunities="result.contribution_opportunities ?? []" :repo-url="store.run?.repo_url" :structure="result.structure" :todos="result.todos" />
      </div>
    </div>
    </Transition>
  </div>
</template>
