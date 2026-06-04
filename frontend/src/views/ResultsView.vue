<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'
import AppTabs from '../components/ui/AppTabs.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppBadge from '../components/ui/AppBadge.vue'
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
import SimilarReposPanel from '../components/analysis/SimilarReposPanel.vue'
import CompareModal from '../components/ui/CompareModal.vue'
import axios from 'axios'

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

const PROGRESS_STEPS: { key: string; label: string }[] = [
  { key: 'cloning',    label: 'Cloning repository…' },
  { key: 'parsing',    label: 'Parsing imports & structure…' },
  { key: 'metadata',   label: 'Fetching GitHub metadata…' },
  { key: 'heuristics', label: 'Computing heuristics…' },
  { key: 'finalizing', label: 'Finalizing results…' },
]

const currentStepIndex = computed(() => {
  const step = store.run?.progress_step
  if (!step) return -1
  return PROGRESS_STEPS.findIndex(s => s.key === step)
})

const currentStepLabel = computed(() => {
  if (isInitialLoading.value) return 'Loading analysis…'
  const step = store.run?.progress_step
  if (!step) return store.run?.status === 'pending' ? 'Queued — waiting for a worker…' : 'Analyzing…'
  return PROGRESS_STEPS.find(s => s.key === step)?.label ?? 'Analyzing…'
})

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

const scrollRef = ref<HTMLElement | null>(null)

function goToChapter(tab: string) {
  activeTab.value = tab
  scrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
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
  store.similarRuns = null
  await store.pollRun(id)
}, { immediate: true })

watch(() => store.run?.status, (status) => {
  if (status === 'completed' && runId.value) {
    store.fetchJitData(runId.value)
    store.fetchDiff(runId.value)
    store.fetchSimilar(runId.value)
  }
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

// Overflow menu (secondary actions)
const showOverflow = ref(false)
function closeOverflow() { showOverflow.value = false }

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
const cardCopied = ref(false)
const cardTheme = ref<'dark' | 'light'>('dark')
// API origin for badge/card SVGs (backend domain in prod); public origin for clickable links (frontend)
const _apiOrigin = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/api\/?$/, '') || window.location.origin
const _publicOrigin = (import.meta.env.VITE_PUBLIC_BASE_URL as string | undefined) || window.location.origin
const badgeUrl = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `${_apiOrigin}/api/v1/repositories/badge/${o}/${n}.svg`
})
const embedMarkdown = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `[![Atlas Insight](${badgeUrl.value})](${_publicOrigin}/r/${o}/${n})`
})
const cardUrl = computed(() => {
  if (!store.run) return ''
  return `${_apiOrigin}/api/v1/repositories/runs/${store.run.id}/card.svg?theme=${cardTheme.value}`
})
const cardMarkdown = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `[![Atlas Insight](${cardUrl.value})](${_publicOrigin}/r/${o}/${n})`
})
function copyEmbed() {
  navigator.clipboard.writeText(embedMarkdown.value)
  embedCopied.value = true
  setTimeout(() => { embedCopied.value = false }, 2000)
}
function copyCard() {
  navigator.clipboard.writeText(cardMarkdown.value)
  cardCopied.value = true
  setTimeout(() => { cardCopied.value = false }, 2000)
}

const showAiSummaryModal = ref(false)
const aiSummaryText = ref('')
const aiSummaryCopied = ref(false)
const aiSummaryLoading = ref(false)

async function openAiSummary() {
  if (!store.run || aiSummaryLoading.value) return
  showAiSummaryModal.value = true
  if (aiSummaryText.value) return  // already loaded
  aiSummaryLoading.value = true
  try {
    const { data } = await axios.get(`/api/v1/repositories/runs/${store.run.id}/ai-summary`)
    aiSummaryText.value = data.summary
  } finally {
    aiSummaryLoading.value = false
  }
}

async function copyAiSummary() {
  if (!aiSummaryText.value) return
  await navigator.clipboard.writeText(aiSummaryText.value)
  aiSummaryCopied.value = true
  setTimeout(() => { aiSummaryCopied.value = false }, 2500)
}

const isArchived = computed(() => result.value?.github_meta?.archived === true)

const showCompareModal = ref(false)

// Sub-project selector state — one ref per panel that has a selector
const activeArchSubProject = ref<string | null>(null)
const activeDepsSubProject = ref<string | null>(null)
const activeHeuristicsSubProject = ref<string | null>(null)

function onTabKey(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement).tagName
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return
  if ((e.target as HTMLElement).isContentEditable) return
  const idx = CHAPTER_TABS.indexOf(activeTab.value)
  if (e.key === 'j') activeTab.value = CHAPTER_TABS[Math.max(idx - 1, 0)]
  else if (e.key === 'k') activeTab.value = CHAPTER_TABS[Math.min(idx + 1, CHAPTER_TABS.length - 1)]
}

onMounted(() => {
  window.addEventListener('keydown', onTabKey)
  document.addEventListener('click', closeOverflow)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onTabKey)
  document.removeEventListener('click', closeOverflow)
  store._stopPolling()
})
</script>

<template>
  <div class="results-layout">

    <!-- ── Sticky shell: header + tabs ─────────────────────────────── -->
    <div class="results-layout__sticky">
      <div class="results-header">
        <a v-if="store.run?.repo_url" :href="store.run.repo_url" target="_blank" rel="noopener noreferrer" class="results-header__repo-link results-header__repo-link--title">
          {{ store.run?.repo_owner }}/{{ store.run?.repo_name }}
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 3H3a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V9"/><polyline points="10 1 15 1 15 6"/><line x1="15" y1="1" x2="7" y2="9"/></svg>
        </a>
        <span v-else class="results-header__title">Analysis Results</span>
        <AppBadge
          v-if="result?.repo_type?.type && result.repo_type.type !== 'single'"
          variant="info"
          style="flex-shrink: 0"
        >{{ result.repo_type.type.toUpperCase() }}</AppBadge>
        <div class="results-header__actions">
          <div class="results-header__action-group">
            <AppButton v-if="result" variant="secondary" size="sm" @click="copyLink">
              {{ copied ? '✓ Copied' : '🔗 Share' }}
            </AppButton>
            <AppButton v-if="result" variant="secondary" size="sm" @click="showCompareModal = true">
              ⇄ Compare
            </AppButton>
            <AppButton v-if="result" variant="secondary" size="sm" @click="showEmbed = !showEmbed">
              {{ showEmbed ? '✕ Embed' : '</> Embed' }}
            </AppButton>
            <div v-if="result" class="results-header__overflow" @click.stop>
              <AppButton variant="secondary" size="sm" @click="showOverflow = !showOverflow" title="More actions">
                Export
              </AppButton>
              <div v-if="showOverflow" class="results-header__overflow-menu">
                <button class="results-header__overflow-item" @click="exportJson(); showOverflow = false">↓ Export JSON</button>
                <button class="results-header__overflow-item" @click="printPage(); showOverflow = false">⎙ Print / PDF</button>
                <button class="results-header__overflow-item" @click="openAiSummary(); showOverflow = false">
                  🤖 AI Summary
                </button>
              </div>
            </div>
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
            <a href="/" class="btn btn--secondary btn--sm">← New</a>
          </div>
        </div>
      </div>
      <AppTabs v-if="result" :tabs="TABS" v-model="activeTab" :badges="tabBadges" />
    </div>

    <!-- ── Scrollable content ───────────────────────────────────────── -->
    <div ref="scrollRef" class="results-layout__scroll">

      <!-- Progress state -->
      <div v-if="showProgress" class="analysis-progress">
        <div class="spinner spinner--xl" />
        <p class="analysis-progress__step">{{ currentStepLabel }}</p>
        <p class="analysis-progress__hint">Typical analyses take 30–90 seconds.</p>
        <div v-if="isPolling && currentStepIndex >= 0" class="analysis-progress__track">
          <span
            v-for="(step, i) in PROGRESS_STEPS"
            :key="step.key"
            :class="['analysis-progress__dot', i === currentStepIndex && 'analysis-progress__dot--active', i < currentStepIndex && 'analysis-progress__dot--done']"
            :title="step.label"
          />
        </div>
        <div v-else-if="isPolling" class="analysis-progress__track">
          <span
            v-for="step in PROGRESS_STEPS"
            :key="step.key"
            class="analysis-progress__dot"
          />
        </div>
      </div>

      <!-- Error state (no result yet) -->
      <div v-if="store.status === 'error' && !result" class="analysis-error-card">
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

      <!-- Result content -->
      <Transition name="fade">
      <div v-if="result">
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
            <div class="embed-panel__row">
              <span class="embed-panel__row-label">Badge</span>
              <div class="embed-panel__snippet">
                <code class="embed-panel__code">{{ embedMarkdown }}</code>
                <button class="btn btn--secondary embed-panel__copy" @click="copyEmbed">
                  {{ embedCopied ? '✓ Copied' : 'Copy' }}
                </button>
              </div>
            </div>
            <div class="embed-panel__row">
              <div class="embed-panel__row-header">
                <span class="embed-panel__row-label">Card</span>
                <div class="embed-panel__theme-toggle">
                  <button class="embed-panel__theme-btn" :class="{ 'embed-panel__theme-btn--active': cardTheme === 'dark' }" @click="cardTheme = 'dark'">Dark</button>
                  <button class="embed-panel__theme-btn" :class="{ 'embed-panel__theme-btn--active': cardTheme === 'light' }" @click="cardTheme = 'light'">Light</button>
                </div>
              </div>
              <div class="embed-panel__snippet">
                <code class="embed-panel__code">{{ cardMarkdown }}</code>
                <button class="btn btn--secondary embed-panel__copy" @click="copyCard">
                  {{ cardCopied ? '✓ Copied' : 'Copy' }}
                </button>
              </div>
            </div>
            <div class="embed-panel__previews">
              <div class="embed-panel__preview-item">
                <span class="embed-panel__preview-label">Badge</span>
                <img :src="badgeUrl" alt="Atlas Insight badge" class="embed-panel__badge-img" loading="lazy" />
              </div>
              <div class="embed-panel__preview-item embed-panel__preview-item--card">
                <span class="embed-panel__preview-label">Card</span>
                <div class="embed-panel__card-bg" :class="{ 'embed-panel__card-bg--light': cardTheme === 'light' }">
                  <img :src="cardUrl" alt="Atlas Insight health card" class="embed-panel__card-img" loading="lazy" />
                </div>
              </div>
            </div>
          </div>
        </Transition>

        <template v-if="activeTab === 'Overview'">
          <div class="overview-split">
            <div class="overview-split__left">
              <OverviewPanel :result="result" :run-id="runId" />
              <SimilarReposPanel
                v-if="store.similarRuns !== null || store.similarLoading"
                :runs="store.similarRuns ?? []"
                :loading="store.similarLoading"
              />
            </div>
            <div class="overview-split__right">
              <AnalysisStatusCard v-if="store.run" :run="store.run" />
              <DeltaPanel
                v-if="store.diffData || store.diffLoading"
                :diff-data="store.diffData ?? { available: false }"
                :loading="store.diffLoading"
              />
            </div>
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
          <ArchitecturePanel
            :graph="result.graph"
            :hot-files="result.structure?.hot_files"
            :structure="result.structure"
            :run-id="runId"
            :repo-url="store.run?.repo_url"
            :sub-projects="result.repo_type?.sub_projects"
            :selected-sub-project="activeArchSubProject"
            @update:selected-sub-project="activeArchSubProject = $event"
          />
          <div style="margin-top: 1.5rem">
            <DependencyGraphView
              :graph="activeArchSubProject && result.repo_type?.sub_projects?.find(sp => sp.name === activeArchSubProject)?.graph || result.graph"
            />
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
        <DependenciesPanel
          v-if="activeTab === 'Dependencies'"
          :deps="result.dependencies"
          :security="result.security"
          :sub-projects="result.repo_type?.sub_projects"
          :selected-sub-project="activeDepsSubProject"
          @update:selected-sub-project="activeDepsSubProject = $event"
        />
        <SecurityPanel v-if="activeTab === 'Security'" :security="result.security" :heuristics="result.heuristics" :structure="result.structure" />
        <HeuristicsPanel
          v-if="activeTab === 'Heuristics'"
          :signals="result.heuristics"
          :result="result"
          :sub-projects="result.repo_type?.sub_projects"
          :selected-sub-project="activeHeuristicsSubProject"
          @update:selected-sub-project="activeHeuristicsSubProject = $event"
        />
        <ContributingPanel v-if="activeTab === 'Contributing'" :opportunities="result.contribution_opportunities ?? []" :repo-url="store.run?.repo_url" :structure="result.structure" :todos="result.todos" :arch-tours="result.arch_tours ?? []" :commits="result.commits" />
        <ArchitectureToursPanel v-if="activeTab === 'Tours'" :tours="result.arch_tours ?? []" :repo-url="store.run?.repo_url" :run-id="runId" />
      </div>
      </Transition>
    </div>

    <!-- ── Pinned chapter nav ───────────────────────────────────────── -->
    <div v-if="result" class="results-layout__chapter-nav">
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

  <CompareModal v-if="showCompareModal" @close="showCompareModal = false" />

  <!-- AI Summary modal -->
  <Teleport to="body">
    <div v-if="showAiSummaryModal" class="ai-summary-overlay" @click.self="showAiSummaryModal = false">
      <div class="ai-summary-modal">
        <div class="ai-summary-modal__header">
          <span class="ai-summary-modal__title">AI Context Block</span>
          <div class="ai-summary-modal__actions">
            <button
              class="ai-summary-modal__copy"
              :disabled="!aiSummaryText"
              @click="copyAiSummary"
            >{{ aiSummaryCopied ? '✓ Copied' : 'Copy' }}</button>
            <button class="ai-summary-modal__close" @click="showAiSummaryModal = false">✕</button>
          </div>
        </div>
        <div v-if="aiSummaryLoading" class="ai-summary-modal__loading">Loading…</div>
        <pre v-else class="ai-summary-modal__body">{{ aiSummaryText }}</pre>
      </div>
    </div>
  </Teleport>
</template>
