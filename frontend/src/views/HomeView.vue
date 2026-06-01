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
import type { RunListItem, FeaturedRepo } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const store = useAnalysisStore()
const auth = useAuthStore()

const GITHUB_RE = /^https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?$/
const initialUrl = ref('')

const featured = ref<FeaturedRepo | null>(null)
const spotlight = ref<any>(null)

interface TrendingRepo {
  run_id: string
  repo_url: string
  repo_owner: string
  repo_name: string
  analysis_count: number
  health_label: string | null
  health_key: string | null
  primary_language: string | null
  stars: number | null
}
const trending = ref<TrendingRepo[]>([])

type BadgeVariant = 'pending' | 'running' | 'completed' | 'failed' | 'warning' | 'info'
const HEALTH_COLORS: Record<string, BadgeVariant> = {
  thriving: 'completed',
  active: 'completed',
  stable: 'warning',
  declining: 'failed',
  abandoned: 'failed',
}

async function fetchFeatured() {
  try {
    const { data } = await axios.get('/api/v1/repositories/featured')
    featured.value = data
  } catch {
    featured.value = null
  }
}

async function fetchSpotlight() {
  try {
    const { data } = await axios.get('/api/v1/repositories/spotlight/current')
    spotlight.value = data
  } catch {
    spotlight.value = null
  }
}

async function fetchTrending() {
  try {
    const { data } = await axios.get('/api/v1/repositories/trending')
    trending.value = data
  } catch {
    trending.value = []
  }
}

onMounted(() => {
  store.error = null
  fetchFeatured()
  fetchSpotlight()
  fetchTrending()

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
    // Sync watchlist from server favorites for authenticated users
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

const pinnedItems = computed(() => items.value.filter(r => watchlist.value.has(r.repo_url)))
const unpinnedItems = computed(() => items.value.filter(r => !watchlist.value.has(r.repo_url)))
const ghostRows = computed(() => Math.max(0, perPage - items.value.length))

</script>

<template>
  <div>
    <main class="hero hero--compact">
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
    </main>

    <div v-if="spotlight" class="featured-section">
      <RepoOfWeekCard :spotlight="spotlight" />
    </div>

    <div v-if="featured" class="featured-section">
      <div class="featured-repo-card">
        <div class="featured-repo-card__eyebrow">Featured Analysis</div>
        <div class="featured-repo-card__content">
          <div class="featured-repo-card__left">
            <h3 class="featured-repo-card__name">
              <a :href="featured.repo_url" target="_blank" rel="noopener noreferrer">
                {{ featured.repo_owner }}/{{ featured.repo_name }} ↗
              </a>
            </h3>
            <p v-if="featured.github_description" class="featured-repo-card__desc">
              {{ featured.github_description }}
            </p>
            <div class="featured-repo-card__meta">
              <span v-if="featured.primary_language" class="featured-repo-card__lang">
                {{ featured.primary_language }}
              </span>
              <span v-if="featured.stars !== null" class="featured-repo-card__stars">
                ★ {{ featured.stars?.toLocaleString() }}
              </span>
              <AppBadge
                v-if="featured.health_label && featured.health_key"
                :variant="(HEALTH_COLORS[featured.health_key] ?? 'info') as BadgeVariant"
              >
                {{ featured.health_label }}
              </AppBadge>
            </div>
            <div v-if="featured.topics.length" class="featured-repo-card__topics">
              <span v-for="t in featured.topics.slice(0, 5)" :key="t" class="featured-repo-card__topic">
                {{ t }}
              </span>
            </div>
          </div>
          <div class="featured-repo-card__action">
            <AppButton variant="primary" @click="router.push(`/results/${featured.run_id}`)">
              Explore full analysis →
            </AppButton>
          </div>
        </div>
      </div>
    </div>

    <div v-if="trending.length" class="trending-section">
      <h2 class="trending-section__title">Trending This Week</h2>
      <div class="trending-section__grid">
        <div
          v-for="repo in trending"
          :key="repo.run_id"
          class="trending-card"
          @click="router.push(`/results/${repo.run_id}`)"
        >
          <div class="trending-card__header">
            <span class="trending-card__owner">{{ repo.repo_owner }}</span>
            <span class="trending-card__sep">/</span>
            <span class="trending-card__name">{{ repo.repo_name }}</span>
          </div>
          <div class="trending-card__meta">
            <span v-if="repo.primary_language" class="trending-card__lang">{{ repo.primary_language }}</span>
            <span v-if="repo.stars !== null" class="trending-card__stars">★ {{ repo.stars?.toLocaleString() }}</span>
          </div>
          <div class="trending-card__footer">
            <AppBadge
              v-if="repo.health_label && repo.health_key"
              :variant="(HEALTH_COLORS[repo.health_key] ?? 'info') as BadgeVariant"
            >{{ repo.health_label }}</AppBadge>
            <span class="trending-card__count">{{ repo.analysis_count }}× this week</span>
          </div>
        </div>
      </div>
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
            <!-- Pinned repos -->
            <template v-if="pinnedItems.length && !q">
              <tr
                v-for="run in pinnedItems"
                :key="'pin-' + run.id"
                class="runs-table__row runs-table__row--pinned"
                @click="goToRun(run.id)"
              >
                <td @click.stop>
                  <button class="runs-table__pin runs-table__pin--active" @click="togglePin(run.repo_url)" title="Unpin">★</button>
                </td>
                <td><span class="runs-table__author">{{ run.repo_owner }}</span></td>
                <td>
                  <div class="runs-table__repo">
                    <span class="runs-table__project">{{ run.repo_name }}</span>
                    <span class="runs-table__url">{{ run.repo_url }}</span>
                  </div>
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
              <tr v-if="unpinnedItems.length" class="runs-table__divider">
                <td colspan="6"><span>Other repos</span></td>
              </tr>
            </template>

            <!-- Regular (unpinned) repos -->
            <tr
              v-for="run in (q ? items : unpinnedItems)"
              :key="run.id"
              class="runs-table__row"
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

            <!-- Ghost rows — keep table height stable at perPage slots -->
            <tr
              v-for="i in ghostRows"
              :key="'ghost-' + i"
              class="runs-table__row runs-table__row--ghost"
            >
              <td colspan="6">&nbsp;</td>
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
