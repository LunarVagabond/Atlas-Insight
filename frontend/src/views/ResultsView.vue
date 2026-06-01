<script setup lang="ts">
import { ref, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'
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
import DeltaPanel from '../components/analysis/DeltaPanel.vue'
import ContributorGraph from '../components/analysis/ContributorGraph.vue'
import StaleBranchesPanel from '../components/analysis/StaleBranchesPanel.vue'

const route = useRoute()
const router = useRouter()
const store = useAnalysisStore()
const auth = useAuthStore()
const runId = computed(() => route.params.runId as string)
const result = computed(() => {
  const r = store.run?.result
  if (!r || r.error) return null
  return r
})
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

const CHAPTER_TABS = ['Overview', 'Project', 'History', 'Architecture', 'Ownership', 'Dependencies', 'Security', 'Heuristics', 'Contributing', 'Tours']
const TABS = computed(() => CHAPTER_TABS)

const tabBadges = computed<Record<string, number | string>>(() => {
  if (!result.value) return {}
  const r = result.value
  const badges: Record<string, number | string> = {}

  const secCount = (r.security?.issue_count ?? 0) + (r.security?.vulnerabilities?.length ?? 0)
  if (secCount > 0) badges['Security'] = secCount

  const contribCount = r.contribution_opportunities?.length ?? 0
  if (contribCount > 0) badges['Contributing'] = contribCount

  const toursCount = r.arch_tours?.length ?? 0
  if (toursCount > 0) badges['Tours'] = toursCount

  const highRiskHeuristics = (r.heuristics ?? []).filter(h => h.score >= 60).length
  if (highRiskHeuristics > 0) badges['Heuristics'] = highRiskHeuristics

  return badges
})

const activeTab = ref((route.query.tab as string) || 'Overview')

const activeChapterIndex = computed(() => CHAPTER_TABS.indexOf(activeTab.value))
const prevChapter = computed(() => activeChapterIndex.value > 0 ? CHAPTER_TABS[activeChapterIndex.value - 1] : null)
const nextChapter = computed(() => activeChapterIndex.value < CHAPTER_TABS.length - 1 ? CHAPTER_TABS[activeChapterIndex.value + 1] : null)

function goToChapter(tab: string) {
  activeTab.value = tab
  window.scrollTo({ top: 0, behavior: 'smooth' })
}


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
  store.diffData = null
  await store.pollRun(id)
}, { immediate: true })

watch(() => store.run?.status, (status) => {
  if (status === 'completed' && runId.value) {
    store.fetchJitData(runId.value)
    store.fetchDiff(runId.value)
  }
})

onUnmounted(() => {
  store._stopPolling()
  if (stepTimer) { clearInterval(stepTimer); stepTimer = null }
})

// Re-analyze with cooldown
const reanalyzing = ref(false)

const cooldownUntil = computed(() => {
  const cu = store.run?.cooldown_until
  if (!cu) return null
  const d = new Date(cu)
  if (d <= new Date()) return null
  return d
})

const cooldownLabel = computed(() => {
  if (!cooldownUntil.value) return null
  const diffMs = cooldownUntil.value.getTime() - Date.now()
  const hours = Math.floor(diffMs / 3_600_000)
  const mins = Math.floor((diffMs % 3_600_000) / 60_000)
  if (hours > 0) return `Available in ${hours}h ${mins}m`
  return `Available in ${mins}m`
})

async function reanalyze() {
  if (!runId.value || cooldownUntil.value) return
  reanalyzing.value = true
  try {
    const newId = await store.retryRun(runId.value)
    router.push(`/results/${newId}`)
  } finally {
    reanalyzing.value = false
  }
}

async function forceReanalyze() {
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

function printPage() {
  window.open(`/print/${runId.value}`, '_blank', 'noopener')
}

// Copy permalink
const copied = ref(false)
function copyLink() {
  const url = `${window.location.origin}/r/${store.run?.repo_owner}/${store.run?.repo_name}`
  navigator.clipboard.writeText(url)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

// Embed / badge snippet
const showEmbed = ref(false)
const embedCopied = ref(false)
const _apiBase = computed(() =>
  (import.meta.env.VITE_API_BASE_URL as string).replace(/\/api$/, '')
)
const badgeUrl = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `${_apiBase.value}/api/v1/repositories/badge/${o}/${n}.svg`
})
const embedMarkdown = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  const link = `${window.location.origin}/r/${o}/${n}`
  return `[![Atlas Insight](${badgeUrl.value})](${link})`
})
const cardUrl = computed(() => {
  if (!store.run) return ''
  return `${_apiBase.value}/api/v1/repositories/runs/${store.run.id}/card.svg`
})
function copyEmbed() {
  navigator.clipboard.writeText(embedMarkdown.value)
  embedCopied.value = true
  setTimeout(() => { embedCopied.value = false }, 2000)
}

const isArchived = computed(() => result.value?.github_meta?.archived === true)
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <div class="results-header">
        <a v-if="store.run?.repo_url" :href="store.run.repo_url" target="_blank" rel="noopener noreferrer" class="results-header__repo-link results-header__repo-link--title">
          {{ store.run?.repo_owner }}/{{ store.run?.repo_name }} ↗
        </a>
        <span v-else class="results-header__title">Analysis Results</span>
        <div class="results-header__actions">
          <div class="results-header__action-group">
            <AppButton v-if="result" variant="secondary" size="sm" @click="copyLink">
              {{ copied ? '✓ Copied' : '🔗 Share' }}
            </AppButton>
            <AppButton v-if="result" variant="secondary" size="sm" @click="showEmbed = !showEmbed">
              {{ showEmbed ? '✕ Embed' : '</> Embed' }}
            </AppButton>
            <AppButton v-if="result" variant="secondary" size="sm" @click="exportJson">
              ↓ Export JSON
            </AppButton>
            <AppButton v-if="result" variant="secondary" size="sm" @click="printPage">
              ⎙ Print / PDF
            </AppButton>
          </div>
          <div class="results-header__action-group">
            <template v-if="store.run?.status === 'completed'">
              <AppButton v-if="!cooldownUntil" variant="secondary" size="sm" :disabled="reanalyzing" @click="reanalyze">
                {{ reanalyzing ? 'Queuing…' : '↻ Re-analyze' }}
              </AppButton>
              <template v-else>
                <span class="cooldown-label" :title="'Re-analysis ' + cooldownLabel">{{ cooldownLabel }}</span>
                <AppButton v-if="auth.user?.is_superuser" variant="secondary" size="sm" :disabled="reanalyzing" @click="forceReanalyze" class="btn--force" title="Superuser: bypass cooldown">
                  {{ reanalyzing ? 'Queuing…' : '⚡ Force Re-scan' }}
                </AppButton>
              </template>
            </template>
            <a href="/" class="btn btn--secondary btn--sm">← New Analysis</a>
          </div>
        </div>
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
          <AppButton variant="primary" :disabled="reanalyzing" @click="reanalyze">
            {{ reanalyzing ? 'Queuing…' : '↻ Re-run Analysis' }}
          </AppButton>
          <a href="/" class="btn btn--secondary">← New Analysis</a>
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
      <div v-if="isArchived" class="archived-banner" role="alert">
        <span class="archived-banner__icon">📦</span>
        <span class="archived-banner__text">This repository is <strong>archived</strong> — read-only, no longer accepting contributions.</span>
      </div>
      <Transition name="fade">
        <div v-if="showEmbed" class="embed-panel">
          <div class="embed-panel__header">
            <span class="embed-panel__title">Embed in README</span>
            <button class="embed-panel__close" @click="showEmbed = false" aria-label="Close embed panel">✕</button>
          </div>
          <p class="embed-panel__hint">Paste this markdown into your repository's README to add an Atlas Insight badge:</p>
          <div class="embed-panel__snippet">
            <code class="embed-panel__code">{{ embedMarkdown }}</code>
            <button class="btn btn--secondary embed-panel__copy" @click="copyEmbed">
              {{ embedCopied ? '✓ Copied' : 'Copy' }}
            </button>
          </div>
          <div class="embed-panel__previews">
            <div class="embed-panel__preview-item">
              <span class="embed-panel__preview-label">Badge</span>
              <img :src="badgeUrl" alt="Atlas Insight badge" class="embed-panel__badge-img" loading="lazy" />
            </div>
            <div class="embed-panel__preview-item">
              <span class="embed-panel__preview-label">Card</span>
              <img :src="cardUrl" alt="Atlas Insight health card" class="embed-panel__card-img" loading="lazy" />
            </div>
          </div>
        </div>
      </Transition>
      <AppTabs :tabs="TABS" v-model="activeTab" :badges="tabBadges" />
      <div style="margin-top: 1.5rem">
        <template v-if="activeTab === 'Overview'">
          <AnalysisStatusCard v-if="store.run" :run="store.run" />
          <DeltaPanel
            v-if="store.diffData || store.diffLoading"
            :diff-data="store.diffData ?? { available: false }"
            :loading="store.diffLoading"
            style="margin-top: 1rem"
          />
          <div style="margin-top: 1.5rem">
            <OverviewPanel :result="result" />
          </div>
        </template>
        <template v-if="activeTab === 'Project'">
          <ProjectPanel :result="result" />
          <div v-if="result.structure" style="margin-top: 1.5rem" class="panel">
            <StaleBranchesPanel
              :stale-branches="result.structure.stale_branches ?? []"
              :stale-branch-count="result.structure.stale_branch_count ?? 0"
            />
          </div>
        </template>
        <template v-if="activeTab === 'History'">
          <CommitTimelineChart :commits="result.commits" :repo-url="store.run?.repo_url" :github-contributors="result.github_meta?.contributors" />
          <div style="margin-top: 1.5rem">
            <ContributorGraph :commits="result.commits" />
          </div>
          <div v-if="hasRoadmap && result.structure?.roadmap_parsed" style="margin-top: 1.5rem" class="panel">
            <RoadmapTimeline
              :milestones="result.structure.roadmap_parsed.milestones"
              :roadmap-file="result.structure.roadmap_file ?? 'ROADMAP.md'"
            />
          </div>
        </template>
        <template v-if="activeTab === 'Architecture'">
          <ArchitecturePanel :graph="result.graph" :hot-files="result.structure?.hot_files" :structure="result.structure" :run-id="runId" :repo-url="store.run?.repo_url" />
          <div style="margin-top: 1.5rem">
            <DependencyGraphView :graph="result.graph" />
          </div>
        </template>
        <div v-if="(activeTab === 'Ownership' || activeTab === 'Contributing') && store.jitError" class="jit-error-notice">
          Could not load live GitHub data (issues / PRs). Showing static analysis only.
        </div>
        <OwnershipPanel
          v-if="activeTab === 'Ownership'"
          :ownership="result.ownership ?? { subsystems: [], top_contributors: [], bus_factor: 0 }"
          :jit-issues="store.jitIssues"
          :jit-loading="store.jitLoading"
          :repo-url="store.run?.repo_url"
          :github-contributors="result.github_meta?.contributors"
          :run-id="runId"
        />
        <DependenciesPanel v-if="activeTab === 'Dependencies'" :deps="result.dependencies" :security="result.security" />
        <SecurityPanel v-if="activeTab === 'Security'" :security="result.security" :heuristics="result.heuristics" :structure="result.structure" />
        <HeuristicsPanel v-if="activeTab === 'Heuristics'" :signals="result.heuristics" :result="result" />
        <ContributingPanel v-if="activeTab === 'Contributing'" :opportunities="result.contribution_opportunities ?? []" :repo-url="store.run?.repo_url" :structure="result.structure" :todos="result.todos" :arch-tours="result.arch_tours ?? []" />
        <ArchitectureToursPanel v-if="activeTab === 'Tours'" :tours="result.arch_tours ?? []" :repo-url="store.run?.repo_url" :run-id="runId" />

        <div class="chapter-nav">
          <button v-if="prevChapter" class="btn btn--secondary chapter-nav__btn" @click="goToChapter(prevChapter)">
            ← {{ prevChapter }}
          </button>
          <span v-else class="chapter-nav__spacer" />
          <span class="chapter-nav__position">
            Ch.{{ activeChapterIndex + 1 }} / {{ CHAPTER_TABS.length }}
          </span>
          <button v-if="nextChapter" class="btn btn--primary chapter-nav__btn" @click="goToChapter(nextChapter)">
            {{ nextChapter }} →
          </button>
          <span v-else class="chapter-nav__spacer" />
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>
