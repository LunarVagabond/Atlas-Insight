<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import URLInputForm from '../components/analysis/URLInputForm.vue'
import RepoOfWeekCard from '../components/analysis/RepoOfWeekCard.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import AppButton from '../components/ui/AppButton.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'
import CompareModal from '../components/ui/CompareModal.vue'
import { useAnalysisStore } from '../stores/analysis'
import type { RunListItem } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'
import logoUrl from '../assets/logo.png'
import LanguageList from '../components/ui/LanguageList.vue'
import { SUPPORTED_LANGUAGES } from '../data/languages'

const router = useRouter()
const route = useRoute()
const store = useAnalysisStore()
const auth = useAuthStore()

const GITHUB_RE = /^https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?$/
const initialUrl = ref('')

const spotlight = ref<any>(null)

async function fetchSpotlight() {
  try {
    const { data } = await axios.get('/api/v1/repositories/spotlight/current')
    spotlight.value = data
  } catch {
    spotlight.value = null
  }
}

onMounted(() => {
  store.error = null
  fetchSpotlight()

  const qUrl = route.query.url as string | undefined
  if (qUrl && GITHUB_RE.test(qUrl.trim())) {
    initialUrl.value = qUrl.trim()
    handleSubmit(qUrl.trim())
  }
})

async function handleSubmit(url: string, pat?: string) {
  try {
    const runId = await store.submitUrl(url, pat)
    router.push(`/results/${runId}`)
  } catch {
    // error shown in form
  }
}

// ── Runs table ──────────────────────────────────────────────────────────────
const q = ref('')
const sort = ref<'triggered_at' | 'status'>('triggered_at')
const order = ref<'desc' | 'asc'>('desc')
const page = ref(1)
const perPage = 10
const showCompareModal = ref(false)
const items = ref<RunListItem[]>([])
const total = ref(0)
const loading = ref(false)

async function fetchRuns() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/repositories/runs/', {
      params: { q: q.value, sort: sort.value, order: order.value, page: page.value, per_page: perPage },
    })
    items.value = data.items
    total.value = data.total
    if (auth.isAuthenticated) {
      watchlist.value = new Set(
        (data.items as RunListItem[]).filter(r => r.is_favorited).map(r => r.repo_url)
      )
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchRuns)
watch([q, sort, order], () => { page.value = 1; fetchRuns() })
watch(page, fetchRuns)

const totalPages = computed(() => Math.ceil(total.value / perPage))

function setSort(field: typeof sort.value) {
  if (sort.value === field) order.value = order.value === 'desc' ? 'asc' : 'desc'
  else { sort.value = field; order.value = 'desc' }
}

function sortIcon(field: string) {
  if (sort.value !== field) return '↕'
  return order.value === 'desc' ? '↓' : '↑'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

function goToRun(id: string) {
  router.push(`/results/${id}`)
}

// ── Watchlist ────────────────────────────────────────────────────────────────
const WATCHLIST_KEY = 'atlas_watchlist'

function loadWatchlist(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '[]')) }
  catch { return new Set() }
}

const watchlist = ref<Set<string>>(loadWatchlist())

function isPinned(repoUrl: string) { return watchlist.value.has(repoUrl) }

async function togglePin(repoUrl: string) {
  const pinned = watchlist.value.has(repoUrl)
  const w = new Set(watchlist.value)
  if (pinned) w.delete(repoUrl)
  else w.add(repoUrl)
  watchlist.value = w

  if (auth.isAuthenticated) {
    const item = items.value.find(r => r.repo_url === repoUrl)
    if (item?.repo_id) {
      try {
        if (pinned) {
          await axios.delete(`/api/v1/repositories/repos/${item.repo_id}/favorite`)
        } else {
          await axios.post(`/api/v1/repositories/repos/${item.repo_id}/favorite`)
        }
      } catch {
        // silent — local state already updated
      }
    }
  } else {
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify([...w]))
  }
}

// Pinned items float to the top within the current page
const sortedItems = computed(() => [
  ...items.value.filter(r => isPinned(r.repo_url)),
  ...items.value.filter(r => !isPinned(r.repo_url)),
])

const ghostRows = computed(() => Math.max(0, perPage - items.value.length))

// ── Language icons ───────────────────────────────────────────────────────────
const LANG_ICON_MAP = new Map(
  SUPPORTED_LANGUAGES.map(l => [l.name.toLowerCase(), l.iconUrl])
)

function langIconUrl(name: string | null): string | null {
  if (!name) return null
  return LANG_ICON_MAP.get(name.toLowerCase()) ?? null
}
</script>

<template>
  <div>
    <main class="hero hero--compact">
      <img :src="logoUrl" alt="Atlas Insight" class="hero__logo" />
      <h1 class="hero__title">Atlas <span>Insight</span></h1>
      <p class="hero__subtitle">
        Paste a repository URL and get a deep analysis of its commit history,
        architecture, dependencies, and health signals.
      </p>
      <URLInputForm
        :loading="store.status === 'submitting'"
        :error="store.error"
        :initial-url="initialUrl"
        @submitted="handleSubmit"
      />
      <div class="hero__lang-section">
        <p class="hero__lang-heading">Supported Languages &amp; Frameworks</p>
        <LanguageList mode="marquee" />
      </div>
      <p class="hero__disclaimer">
        🧪 Experimental hobby project — results are public and cached. Private repos at your own risk.
      </p>
    </main>

    <div v-if="spotlight" class="home-discovery">
      <RepoOfWeekCard :spotlight="spotlight" />
    </div>

    <div class="home-runs">
      <div class="home-runs__header">
        <h2 class="home-runs__title">Recent Analyses</h2>
        <div class="home-runs__controls">
          <input
            v-model="q"
            class="url-form__input"
            placeholder="Search by URL, project name, or author…"
            style="max-width:320px"
          />
          <span class="runs-search__count">{{ total }} repo{{ total !== 1 ? 's' : '' }}</span>
          <AppButton variant="secondary" @click="showCompareModal = true">
            Compare
          </AppButton>
        </div>
      </div>

      <LoadingSpinner v-if="loading && !items.length" label="Loading…" />

      <div v-else-if="!items.length" class="empty-state" style="padding: 3rem 0">
        No analyses yet{{ q ? ` matching "${q}"` : '' }}. Submit a repo above to get started.
      </div>

      <template v-else>
        <table class="data-table runs-table">
          <thead>
            <tr>
              <th style="width:2rem"></th>
              <th>Author</th>
              <th>Repository</th>
              <th>Primary Language</th>
              <th class="runs-table__sortable" @click="setSort('status')">
                Status {{ sortIcon('status') }}
              </th>
              <th class="runs-table__sortable" @click="setSort('triggered_at')">
                Last Scan {{ sortIcon('triggered_at') }}
              </th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in sortedItems"
              :key="run.id"
              :class="['runs-table__row', isPinned(run.repo_url) && 'runs-table__row--pinned']"
              @click="goToRun(run.id)"
            >
              <td @click.stop>
                <button
                  :class="['runs-table__pin', { 'runs-table__pin--active': isPinned(run.repo_url) }]"
                  @click="togglePin(run.repo_url)"
                  :title="isPinned(run.repo_url) ? 'Unpin' : 'Pin to top'"
                >{{ isPinned(run.repo_url) ? '★' : '☆' }}</button>
              </td>
              <td><span class="runs-table__author">{{ run.repo_owner }}</span></td>
              <td>
                <div class="runs-table__repo">
                  <span class="runs-table__project">{{ run.repo_name }}</span>
                  <span class="runs-table__url">{{ run.repo_url }}</span>
                </div>
              </td>
              <td class="runs-table__lang-cell">
                <template v-if="run.primary_language">
                  <img
                    v-if="langIconUrl(run.primary_language)"
                    :src="langIconUrl(run.primary_language)!"
                    :alt="run.primary_language"
                    class="runs-table__lang-icon"
                    width="16"
                    height="16"
                  />
                  <span v-else class="runs-table__lang-unknown" title="Unknown language">?</span>
                  <span class="runs-table__lang-name">{{ run.primary_language }}</span>
                </template>
                <span v-else class="runs-table__lang-empty">—</span>
              </td>
              <td>
                <div style="display:flex;align-items:center;gap:0.5rem">
                  <AppBadge :variant="run.status">{{ run.status }}</AppBadge>
                  <AppBadge v-if="run.is_stale" variant="warning">Stale</AppBadge>
                </div>
              </td>
              <td>{{ formatDate(run.triggered_at) }}</td>
              <td>
                <AppButton variant="secondary" @click.stop="goToRun(run.id)" style="font-size:0.8125rem;padding:4px 12px">View</AppButton>
              </td>
            </tr>

            <tr
              v-for="i in ghostRows"
              :key="'ghost-' + i"
              class="runs-table__row runs-table__row--ghost"
            >
              <td colspan="7">&nbsp;</td>
            </tr>
          </tbody>
        </table>

        <div v-if="totalPages > 1" class="runs-pagination">
          <AppButton variant="secondary" :disabled="page <= 1" @click="page--">← Prev</AppButton>
          <span class="runs-pagination__info">Page {{ page }} of {{ totalPages }}</span>
          <AppButton variant="secondary" :disabled="page >= totalPages" @click="page++">Next →</AppButton>
        </div>
      </template>
    </div>
  </div>

  <CompareModal v-if="showCompareModal" @close="showCompareModal = false" />
</template>
