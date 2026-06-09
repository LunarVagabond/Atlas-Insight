<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'
import AppTabGroups from '../components/ui/AppTabGroups.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import AppBranchSelect from '../components/ui/AppBranchSelect.vue'
import AnalysisStatusCard from '../components/analysis/AnalysisStatusCard.vue'
import OverviewPanel from '../components/analysis/OverviewPanel.vue'
import CommitTimelineChart from '../components/analysis/CommitTimelineChart.vue'
import ArchitecturePanel from '../components/analysis/ArchitecturePanel.vue'
import DependencyGraphView from '../components/analysis/DependencyGraphView.vue'
import DependenciesPanel from '../components/analysis/DependenciesPanel.vue'
import HeuristicsPanel from '../components/analysis/HeuristicsPanel.vue'
import ProjectPanel from '../components/analysis/ProjectPanel.vue'
import ContributingPanel from '../components/analysis/ContributingPanel.vue'
import ContributionPathPanel from '../components/analysis/ContributionPathPanel.vue'
import RoadmapTimeline from '../components/analysis/RoadmapTimeline.vue'
import SecurityPanel from '../components/analysis/SecurityPanel.vue'
import ArchitectureToursPanel from '../components/analysis/ArchitectureToursPanel.vue'
import OwnershipPanel from '../components/analysis/OwnershipPanel.vue'
import LicensePanel from '../components/analysis/LicensePanel.vue'
import CodeQualityPanel from '../components/analysis/CodeQualityPanel.vue'
import DevOpsPanel from '../components/analysis/DevOpsPanel.vue'
import DeltaPanel from '../components/analysis/DeltaPanel.vue'
import LeaderboardsPanel from '../components/analysis/LeaderboardsPanel.vue'
import CommunityFilesPanel from '../components/analysis/CommunityFilesPanel.vue'
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

const CHAPTER_GROUPS = [
  { label: 'Health',    tabs: ['Overview', 'Heuristics', 'Security', 'Licenses', 'Dependencies'], color: '#f59e0b' },
  { label: 'Codebase',  tabs: ['Architecture', 'Code Quality', 'Project', 'History', 'Ownership'], color: '#6366f1' },
  { label: 'Community', tabs: ['Contributing', 'Contribution Path', 'Community Files', 'Leaderboards', 'DevOps', 'Tours'], color: '#22c55e' },
]
const DOCS_ONLY_TABS = new Set(['Overview', 'Project', 'History', 'Ownership', 'Security', 'Contributing', 'Community Files'])
const isDocsOnly = computed(() => result.value?.is_docs_only === true)

const scoringMode = computed(
  () => result.value?.scoring_mode ?? result.value?.oss_score?.mode ?? null,
)

const scoringModeTag = computed(() => {
  if (scoringMode.value === 'closed_source') return 'Closed source'
  if (scoringMode.value === 'oss') return 'Open source'
  return null
})

const scoringModeTooltip = computed(() => {
  const reason = result.value?.scoring_mode_reason
  if (!scoringMode.value) return undefined
  if (reason) return `Scoring mode: ${reason}`
  return scoringMode.value === 'closed_source'
    ? 'Scored with closed-source expectations (community OSS files not required)'
    : 'Scored with open-source expectations'
})
const GROUPS = computed(() =>
  CHAPTER_GROUPS
    .map(g => ({
      label: g.label,
      color: g.color,
      tabs: isDocsOnly.value ? g.tabs.filter(t => DOCS_ONLY_TABS.has(t)) : g.tabs,
    }))
    .filter(g => g.tabs.length > 0)
)
// Flat tab order derived from groups — keeps j/k navigation aligned with visual group order
const TABS = computed(() => GROUPS.value.flatMap(g => g.tabs))

const tabBadges = computed<Record<string, number | string>>(() => {
  if (!result.value) return {}
  const r = result.value
  const badges: Record<string, number | string> = {}

  const secCount = (r.security?.issue_count ?? 0) + (r.security?.vulnerabilities?.length ?? 0)
  if (secCount > 0) badges['Security'] = secCount

  const contribCount = r.contribution_opportunities?.length ?? 0
  if (contribCount > 0) badges['Contributing'] = contribCount

  const communityGap = r.structure?.community_health
    ? Math.max(0, Math.round((r.structure.community_health.potential_score ?? 0) - (r.structure.community_health.score ?? 0)))
    : 0
  if (communityGap > 0) badges['Community Files'] = communityGap

  const contributorCount = r.commits?.contributor_stats?.length ?? r.commits?.total_contributors ?? 0
  if (contributorCount > 0) badges['Leaderboards'] = contributorCount

  const toursCount = r.arch_tours?.length ?? 0
  if (toursCount > 0) badges['Contribution Path'] = toursCount
  if (toursCount > 0) badges['Tours'] = toursCount

  const highRiskHeuristics = (r.heuristics ?? []).filter(h => h.score >= 60).length
  if (highRiskHeuristics > 0) badges['Heuristics'] = highRiskHeuristics

  const licenseIssues = r.license?.issues?.length ?? 0
  if (licenseIssues > 0) badges['Licenses'] = licenseIssues

  const complexityHotspots = r.complexity?.files_over_threshold ?? 0
  if (complexityHotspots > 0) badges['Code Quality'] = complexityHotspots

  const containerIssues = r.containers?.total_issues ?? 0
  const terraformIssues = r.tools?.terraform?.security_issues?.length ?? 0
  const devopsIssues = containerIssues + terraformIssues
  if (devopsIssues > 0) badges['DevOps'] = devopsIssues

  return badges
})

const activeTab = ref((route.query.tab as string) || 'Overview')

const activeGroupColor = computed(() =>
  GROUPS.value.find(g => g.tabs.includes(activeTab.value))?.color ?? 'var(--color-border)'
)

const activeChapterIndex = computed(() => TABS.value.indexOf(activeTab.value))
const prevChapter = computed(() => activeChapterIndex.value > 0 ? TABS.value[activeChapterIndex.value - 1] : null)
const nextChapter = computed(() => activeChapterIndex.value < TABS.value.length - 1 ? TABS.value[activeChapterIndex.value + 1] : null)

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
  store.branches = null
  store.scannedBranches = null
  await store.pollRun(id)
}, { immediate: true })

watch(() => store.run?.status, (status) => {
  if (status === 'completed' && runId.value) {
    if (!store.branches && !store.branchesLoading) {
      store.fetchBranches(runId.value)
    }
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
  } catch {
    // toast already shown by store
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
  } catch {
    // toast already shown by store
  } finally {
    reanalyzing.value = false
  }
}

const switchingBranch = ref(false)

async function onBranchSelect(branch: string) {
  if (!store.run || branch === (store.run.branch || '')) return
  switchingBranch.value = true
  try {
    // Check if we already have a completed run for this branch
    const owner = store.run.repo_owner
    const name = store.run.repo_name
    const branchParam = `?branch=${encodeURIComponent(branch)}`
    try {
      const { data } = await axios.get(`/api/v1/repositories/by-slug/${owner}/${name}${branchParam}`)
      if (data.run_id && data.status === 'completed') {
        router.push(`/results/${data.run_id}`)
        return
      }
    } catch {
      // No existing run — fall through to submit
    }
    const newId = await store.submitBranch(branch)
    router.push(`/results/${newId}`)
  } finally {
    switchingBranch.value = false
  }
}

// Export JSON
function exportJson() {
  if (!result.value || !store.run) return
  const r = result.value
  const run = store.run
  const branch = run.branch || ''
  const payload = {
    export_version: '2' as const,
    exported_at: new Date().toISOString(),
    run: {
      id: run.id,
      repo_owner: run.repo_owner,
      repo_name: run.repo_name,
      branch,
      url: run.repo_url,
      triggered_at: run.triggered_at,
      completed_at: run.completed_at,
    },
    scoring: {
      mode: r.scoring_mode ?? r.oss_score?.mode ?? null,
      mode_reason: r.scoring_mode_reason ?? r.oss_score?.mode_reason ?? null,
      oss_score: r.oss_score ?? null,
      heuristics: r.heuristics ?? [],
      classification: r.classification ?? null,
    },
    repository: {
      readme: r.readme ?? null,
      structure: r.structure ?? null,
      github_meta: r.github_meta ?? null,
      commits: r.commits ?? null,
      ownership: r.ownership ?? null,
    },
    analysis: {
      graph: r.graph ?? null,
      dependencies: r.dependencies ?? null,
      security: r.security ?? null,
      todos: r.todos ?? null,
      contribution_opportunities: r.contribution_opportunities ?? [],
      arch_tours: r.arch_tours ?? [],
      repo_type: r.repo_type ?? null,
    },
    quality: {
      complexity: r.complexity ?? null,
      dead_code: r.dead_code ?? null,
      test_coverage: r.test_coverage ?? null,
      license: r.license ?? null,
    },
    devops: {
      cicd: r.cicd ?? null,
      containers: r.containers ?? null,
      tools: r.tools ?? null,
      changelog: r.changelog ?? null,
    },
    context: {
      diff: r.diff ?? null,
      similar_runs: r.similar_runs ?? null,
      issues: r.issues ?? null,
      pr_refs: r.pr_refs ?? null,
      is_docs_only: r.is_docs_only ?? false,
    },
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const branchSegment = branch ? `-${branch.replace(/\//g, '-')}` : ''
  a.download = `${store.run.repo_owner}-${store.run.repo_name}${branchSegment}-analysis.json`
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
  const branch = store.run?.branch || ''
  const base = `${window.location.origin}/r/${store.run?.repo_owner}/${store.run?.repo_name}`
  const url = branch ? `${base}?branch=${encodeURIComponent(branch)}` : base
  navigator.clipboard.writeText(url)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

// Embed / badge snippet
const showEmbed = ref(false)
const embedCopied = ref(false)
const cardCopied = ref(false)
const cardTheme = ref<'dark' | 'light'>('dark')
function resolvePublicOrigin(raw: string | undefined): string {
  const fallback = window.location.origin
  if (!raw) return fallback
  try {
    const parsed = new URL(raw)
    const localHosts = new Set(['localhost', '127.0.0.1', '0.0.0.0'])
    const fallbackHost = window.location.hostname
    const fallbackIsLocal = localHosts.has(fallbackHost)
    const parsedIsLocal = localHosts.has(parsed.hostname)
    // Avoid leaking localhost into generated embed links when running on a real domain.
    if (!fallbackIsLocal && parsedIsLocal) return fallback
    return parsed.origin
  } catch {
    return fallback
  }
}
// API origin for badge/card SVGs (backend domain in prod); public origin for clickable links (frontend)
const _apiOrigin = resolvePublicOrigin((import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/api\/?$/, ''))
const _publicOrigin = resolvePublicOrigin(import.meta.env.VITE_PUBLIC_BASE_URL as string | undefined)
const badgeUrl = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `${_apiOrigin}/api/v1/repositories/badge/${o}/${n}.svg`
})
const badgePreviewUrl = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `/api/v1/repositories/badge/${o}/${n}.svg`
})

const _runBranch = computed(() => store.run?.branch || '')
const embedMarkdown = computed(() => {
  if (!store.run) return ''
  const { repo_owner: o, repo_name: n } = store.run
  return `[![Atlas Insight](${badgeUrl.value})](${_publicOrigin}/r/${o}/${n})`
})
const cardUrl = computed(() => {
  if (!store.run) return ''
  const branch = _runBranch.value ? `&branch=${encodeURIComponent(_runBranch.value)}` : ''
  return `${_apiOrigin}/api/v1/repositories/runs/${store.run.id}/card.svg?theme=${cardTheme.value}${branch}`
})
const cardPreviewUrl = computed(() => {
  if (!store.run) return ''
  const branch = _runBranch.value ? `&branch=${encodeURIComponent(_runBranch.value)}` : ''
  return `/api/v1/repositories/runs/${store.run.id}/card.svg?theme=${cardTheme.value}${branch}`
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
  const tabs = TABS.value
  const idx = tabs.indexOf(activeTab.value)
  if (e.key === 'j') activeTab.value = tabs[Math.max(idx - 1, 0)]
  else if (e.key === 'k') activeTab.value = tabs[Math.min(idx + 1, tabs.length - 1)]
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
                  🤖 External AI Context
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
      <div v-if="result && (store.branches !== null || store.branchesLoading)" class="results-header__branch-row">
        <AppBranchSelect
          v-if="store.branches !== null"
          :branches="store.branches"
          :scanned="store.scannedBranches ?? []"
          :default-branch="result?.github_meta?.default_branch"
          :model-value="store.run?.branch || ''"
          :loading="switchingBranch"
          @update:model-value="onBranchSelect"
        />
        <span v-else class="branch-select__loading">Loading branches…</span>
        <span v-if="store.branchesError" class="branch-total-count branch-total-count--error">
          Branch list unavailable
        </span>
        <span v-else-if="store.branches !== null && store.branches.length === 0" class="branch-total-count branch-total-count--error">
          No branches found — org repos may need a PAT (re-submit from home with PAT)
        </span>
        <span v-else-if="store.branches !== null" class="branch-total-count">
          ({{ store.branches.length }} total branches)
        </span>
        <span
          v-if="scoringModeTag"
          class="scoring-mode-badge"
          :class="scoringMode === 'closed_source' ? 'scoring-mode-badge--closed' : 'scoring-mode-badge--oss'"
          :title="scoringModeTooltip"
        >{{ scoringModeTag }}</span>
        <span v-if="isDocsOnly" class="docs-only-header-note">📄 Documentation repository — code analysis tabs hidden</span>
        <span v-if="result.commits?.abandoned" class="branch-stale-badge" title="No commits in the last year — this branch is inactive">
          Stale branch
        </span>
      </div>
      <AppTabGroups v-if="result" :groups="GROUPS" v-model="activeTab" :badges="tabBadges" />
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
      <div v-if="result" class="results-layout__tab-frame" :style="{ '--tab-color': activeGroupColor }">
      <Transition name="fade">
      <div>
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
                <img :src="badgePreviewUrl" alt="Atlas Insight badge" class="embed-panel__badge-img" loading="lazy" />
              </div>
              <div class="embed-panel__preview-item embed-panel__preview-item--card">
                <span class="embed-panel__preview-label">Card</span>
                <div class="embed-panel__card-bg" :class="{ 'embed-panel__card-bg--light': cardTheme === 'light' }">
                  <img :src="cardPreviewUrl" alt="Atlas Insight health card" class="embed-panel__card-img" loading="lazy" />
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
                v-if="result.similar_runs !== undefined"
                :runs="result.similar_runs ?? []"
                :loading="false"
              />
            </div>
            <div class="overview-split__right">
              <AnalysisStatusCard v-if="store.run" :run="store.run" />
              <DeltaPanel
                v-if="result.diff"
                :diff-data="result.diff"
                :loading="false"
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
          <CommitTimelineChart
            :commits="result.commits"
            :repo-url="store.run?.repo_url"
            :github-contributors="result.github_meta?.contributors"
          />
          <div v-if="hasRoadmap && result.structure?.roadmap_parsed" style="margin-top: 1.5rem" class="panel">
            <RoadmapTimeline
              :milestones="result.structure.roadmap_parsed.milestones"
              :roadmap-file="result.structure.roadmap_file ?? 'ROADMAP.md'"
            />
          </div>
        </template>
        <template v-if="activeTab === 'Leaderboards'">
          <LeaderboardsPanel
            :commits="result.commits"
            :github-contributors="result.github_meta?.contributors"
          />
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
        <OwnershipPanel
          v-if="activeTab === 'Ownership'"
          :ownership="result.ownership ?? { subsystems: [], top_contributors: [], bus_factor: 0 }"
          :jit-issues="result.issues ?? null"
          :jit-loading="false"
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
        <LicensePanel v-if="activeTab === 'Licenses'" :license="result.license" />
        <CodeQualityPanel
          v-if="activeTab === 'Code Quality'"
          :complexity="result.complexity"
          :dead-code="result.dead_code"
          :test-coverage="result.test_coverage"
          :structure="result.structure"
        />
        <DevOpsPanel
          v-if="activeTab === 'DevOps'"
          :cicd="result.cicd"
          :containers="result.containers"
          :changelog="result.changelog"
          :tools="result.tools"
        />
        <ContributingPanel v-if="activeTab === 'Contributing'" :opportunities="result.contribution_opportunities ?? []" :repo-url="store.run?.repo_url" :structure="result.structure" :todos="result.todos" :arch-tours="result.arch_tours ?? []" :commits="result.commits" :is-docs-only="isDocsOnly" :github-meta="result.github_meta" />
        <ContributionPathPanel
          v-if="activeTab === 'Contribution Path'"
          :tours="result.arch_tours ?? []"
          :opportunities="result.contribution_opportunities ?? []"
          :repo-url="store.run?.repo_url"
          :all-files="result.structure?.all_files"
        />
        <CommunityFilesPanel v-if="activeTab === 'Community Files'" :result="result" />
        <ArchitectureToursPanel v-if="activeTab === 'Tours'" :tours="result.arch_tours ?? []" :repo-url="store.run?.repo_url" :run-id="runId" />
      </div>
      </Transition>
      </div><!-- /.results-layout__tab-frame -->
    </div>

    <!-- ── Pinned chapter nav ───────────────────────────────────────── -->
    <div v-if="result" class="results-layout__chapter-nav">
      <button v-if="prevChapter" class="btn btn--secondary chapter-nav__btn" @click="goToChapter(prevChapter)">
        ← {{ prevChapter }}
      </button>
      <span v-else class="chapter-nav__spacer" />
      <span class="chapter-nav__position">
        Ch.{{ activeChapterIndex + 1 }} / {{ TABS.length }}
      </span>
      <button v-if="nextChapter" class="btn btn--primary chapter-nav__btn" @click="goToChapter(nextChapter)">
        {{ nextChapter }} →
      </button>
      <span v-else class="chapter-nav__spacer" />
    </div>

  </div>

  <CompareModal v-if="showCompareModal" @close="showCompareModal = false" />

  <!-- External AI context modal -->
  <Teleport to="body">
    <div v-if="showAiSummaryModal" class="ai-summary-overlay" @click.self="showAiSummaryModal = false">
      <div class="ai-summary-modal">
        <div class="ai-summary-modal__header">
          <span class="ai-summary-modal__title">External AI Context Block</span>
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
