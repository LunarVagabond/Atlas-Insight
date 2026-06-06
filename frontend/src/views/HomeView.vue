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
const showFavoritesOnly = ref(false)
const items = ref<RunListItem[]>([])
const total = ref(0)
const loading = ref(false)

async function fetchRuns() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      q: q.value,
      sort: sort.value,
      order: order.value,
      page: page.value,
      per_page: perPage,
    }
    if (showFavoritesOnly.value && auth.isAuthenticated) {
      params.favorited_only = true
    }
    const { data } = await axios.get('/api/v1/repositories/runs/', { params })
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
watch([q, sort, order, showFavoritesOnly], () => { page.value = 1; fetchRuns() })
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

// For unauthenticated users, filter client-side from localStorage watchlist
const displayedItems = computed(() => {
  if (showFavoritesOnly.value && !auth.isAuthenticated) {
    return items.value.filter(r => isPinned(r.repo_url))
  }
  return items.value
})

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
        Paste a repository URL and get a deep static analysis of its commit history,
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
          <AppButton
            :variant="showFavoritesOnly ? 'primary' : 'secondary'"
            @click="showFavoritesOnly = !showFavoritesOnly"
            title="Toggle favorites filter"
          >
            {{ showFavoritesOnly ? '★ Favorites' : '☆ Favorites' }}
          </AppButton>
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
        <div class="home-runs__table-wrap">
        <table class="data-table runs-table">
          <thead>
            <tr>
              <th style="width:2rem"></th>
              <th class="runs-table__author-th">Author</th>
              <th>Repository</th>
              <th>Primary Language(s)</th>
              <th class="runs-table__sortable" @click="setSort('status')">
                Status {{ sortIcon('status') }}
              </th>
              <th class="runs-table__branches-th">Branches</th>
              <th class="runs-table__forks-th">Forks</th>
              <th>Health</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in displayedItems"
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
              <td class="runs-table__author-cell"><span class="runs-table__author">{{ run.repo_owner }}</span></td>
              <td>
                <div class="runs-table__repo">
                  <span class="runs-table__project">{{ run.repo_name }}</span>
                  <span class="runs-table__url">{{ run.repo_url }}</span>
                </div>
              </td>
              <td class="runs-table__lang-cell">
                <template v-if="run.top_languages.length">
                  <template v-for="lang in run.top_languages" :key="lang.name">
                    <img
                      v-if="langIconUrl(lang.name)"
                      :src="langIconUrl(lang.name)!"
                      :alt="lang.name"
                      :title="`${lang.name} (${lang.pct}%)`"
                      class="runs-table__lang-icon"
                      width="16"
                      height="16"
                    />
                  </template>
                </template>
                <span v-else class="runs-table__lang-empty">—</span>
              </td>
              <td>
                <div style="display:flex;align-items:center;gap:0.5rem">
                  <AppBadge :variant="run.status">{{ run.status }}</AppBadge>
                  <AppBadge v-if="run.is_stale" variant="warning">Stale</AppBadge>
                </div>
              </td>
              <td class="runs-table__branches-cell">
                <span v-if="run.scanned_branch_count > 0" class="runs-table__branch-count">
                  {{ run.scanned_branch_count }}<template v-if="run.cached_branch_count != null"> / {{ run.cached_branch_count }}</template>
                </span>
                <span v-else class="runs-table__branch-count runs-table__branch-count--none">—</span>
              </td>
              <td class="runs-table__forks-cell">
                <span v-if="run.fork_count != null" class="runs-table__fork-count">{{ run.fork_count.toLocaleString() }}</span>
                <span v-else class="runs-table__branch-count runs-table__branch-count--none">—</span>
              </td>
              <td class="runs-table__health-cell">
                <span
                  v-if="run.oss_badge"
                  class="runs-table__health-badge"
                  :class="`runs-table__health-badge--${run.oss_badge}`"
                  :title="`${run.oss_score?.toFixed(1)}/10`"
                >{{ run.oss_badge }}</span>
                <span v-else class="runs-table__lang-empty">—</span>
              </td>
            </tr>

            <tr
              v-for="i in ghostRows"
              :key="'ghost-' + i"
              class="runs-table__row runs-table__row--ghost"
            >
              <td colspan="8">&nbsp;</td>
            </tr>
          </tbody>
        </table>
        </div>

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
