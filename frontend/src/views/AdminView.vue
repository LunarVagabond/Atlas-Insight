<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import AppCard from '../components/ui/AppCard.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'

interface AdminStats {
  total_repos: number
  total_runs: number
  queue_depth: number
  failed_runs: number
  completed_runs: number
  repo_clone_count: number
  cache_size_gb: number
}

interface RateLimit {
  limit: number
  remaining: number
  reset_at: string | null
}

interface RateLimitData {
  core: RateLimit
  search: RateLimit
  graphql: RateLimit
}

interface WatchedRepo {
  id: string
  url: string
  owner: string
  name: string
  is_stale: boolean
  last_analyzed_at: string | null
}

const stats = ref<AdminStats | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const accessDenied = ref(false)

const rateLimit = ref<RateLimitData | null>(null)
const rateLimitLoading = ref(false)
const rateLimitError = ref<string | null>(null)

const watchedRepos = ref<WatchedRepo[]>([])
const watchedLoading = ref(false)
const watchedError = ref<string | null>(null)
const isSuperuser = ref(false)

const watchSearchQuery = ref('')
const watchSearchResults = ref<{ id: string; owner: string; name: string; url: string }[]>([])
const watchSearchLoading = ref(false)

async function fetchStats() {
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get<AdminStats>('/api/v1/repositories/admin/stats')
    stats.value = data
    // If staff access works, try superuser endpoints
    fetchWatched()
    fetchRateLimit()
  } catch (err: any) {
    if (err?.response?.status === 403) {
      accessDenied.value = true
    } else {
      error.value = 'Failed to load admin stats'
    }
  } finally {
    loading.value = false
  }
}

async function fetchRateLimit() {
  rateLimitLoading.value = true
  rateLimitError.value = null
  try {
    const { data } = await axios.get<RateLimitData>('/api/v1/repositories/admin/rate-limit')
    rateLimit.value = data
  } catch {
    rateLimitError.value = 'Failed to fetch rate limit'
  } finally {
    rateLimitLoading.value = false
  }
}

async function fetchWatched() {
  watchedLoading.value = true
  watchedError.value = null
  try {
    const { data } = await axios.get<WatchedRepo[]>('/api/v1/repositories/watched')
    watchedRepos.value = data
    isSuperuser.value = true
  } catch (err: any) {
    if (err?.response?.status !== 403) {
      watchedError.value = 'Failed to load watched repos'
    }
  } finally {
    watchedLoading.value = false
  }
}

async function unwatch(repoId: string) {
  await axios.delete(`/api/v1/repositories/repos/${repoId}/watch`)
  watchedRepos.value = watchedRepos.value.filter(r => r.id !== repoId)
}

let _searchTimer: ReturnType<typeof setTimeout> | null = null

async function searchRepos() {
  const q = watchSearchQuery.value.trim()
  if (!q) { watchSearchResults.value = []; return }
  watchSearchLoading.value = true
  try {
    const { data } = await axios.get('/api/v1/repositories/runs/', {
      params: { q, per_page: 10 },
    })
    const watchedIds = new Set(watchedRepos.value.map(r => r.id))
    const seen = new Set<string>()
    watchSearchResults.value = (data.items ?? [])
      .filter((r: any) => !watchedIds.has(r.repo_id) && !seen.has(r.repo_id) && seen.add(r.repo_id))
      .map((r: any) => ({ id: r.repo_id, owner: r.repo_owner, name: r.repo_name, url: r.repo_url }))
  } catch {
    // silent
  } finally {
    watchSearchLoading.value = false
  }
}

function onWatchSearchInput() {
  if (_searchTimer) clearTimeout(_searchTimer)
  if (!watchSearchQuery.value.trim()) { watchSearchResults.value = []; return }
  _searchTimer = setTimeout(searchRepos, 300)
}

function clearWatchSearch() {
  watchSearchQuery.value = ''
  watchSearchResults.value = []
}

async function watch(repo: { id: string; owner: string; name: string; url: string }) {
  await axios.post(`/api/v1/repositories/repos/${repo.id}/watch`)
  watchedRepos.value.push({ ...repo, is_stale: false, last_analyzed_at: null })
  watchSearchResults.value = watchSearchResults.value.filter(r => r.id !== repo.id)
}

function resetAt(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleTimeString()
}

interface SpotlightResult {
  owner: string
  name: string
  url: string
  week_start: string
  pick_number: number
}

const spotlightLoading = ref(false)
const spotlightResult = ref<SpotlightResult | null>(null)
const spotlightError = ref<string | null>(null)

async function pickSpotlight() {
  spotlightLoading.value = true
  spotlightError.value = null
  spotlightResult.value = null
  try {
    const { data } = await axios.post<SpotlightResult>('/api/v1/repositories/admin/pick-spotlight')
    spotlightResult.value = data
  } catch (err: any) {
    spotlightError.value = err?.response?.data?.detail ?? 'Failed to pick spotlight'
  } finally {
    spotlightLoading.value = false
  }
}

function ratePct(r: RateLimit): number {
  if (!r.limit) return 0
  return Math.round((r.remaining / r.limit) * 100)
}

function rateVariant(r: RateLimit): 'failed' | 'warning' | 'completed' {
  const pct = ratePct(r)
  if (pct < 10) return 'failed'
  if (pct < 30) return 'warning'
  return 'completed'
}

onMounted(fetchStats)
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <h1 class="panel__title" style="font-size:1.5rem">Ops Dashboard</h1>
    </div>

    <div class="results-layout__content">
      <div v-if="accessDenied" class="empty-state">
        Staff access only.
      </div>

      <LoadingSpinner v-else-if="loading" label="Loading stats…" />

      <div v-else-if="error" class="empty-state">{{ error }}</div>

      <template v-else-if="stats">
        <!-- System Health -->
        <div class="panel">
          <p class="panel__title">System Health</p>
          <div class="panel__grid">
            <AppCard>
              <div class="stat__value">{{ stats.total_repos }}</div>
              <div class="stat__label">Total Repos</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.total_runs }}</div>
              <div class="stat__label">Total Runs</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.queue_depth }}</div>
              <div class="stat__label">Queue Depth</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.failed_runs }}</div>
              <div class="stat__label">Failed Runs</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.completed_runs }}</div>
              <div class="stat__label">Completed Runs</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.repo_clone_count }}</div>
              <div class="stat__label">Cached Clones</div>
            </AppCard>
            <AppCard>
              <div class="stat__value">{{ stats.cache_size_gb }} GB</div>
              <div class="stat__label">Cache Size</div>
            </AppCard>
          </div>
        </div>

        <!-- GitHub Rate Limit -->
        <div class="panel" style="margin-top:1.5rem">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
            <p class="panel__title" style="margin:0">GitHub Rate Limit</p>
            <AppButton variant="secondary" :disabled="rateLimitLoading" @click="fetchRateLimit">
              {{ rateLimitLoading ? 'Refreshing…' : 'Refresh' }}
            </AppButton>
          </div>
          <div v-if="rateLimitError" class="empty-state">{{ rateLimitError }}</div>
          <div v-else-if="rateLimit" class="rate-limit-grid">
            <AppCard v-for="(rl, key) in { Core: rateLimit.core, Search: rateLimit.search, GraphQL: rateLimit.graphql }" :key="key">
              <div class="rate-limit-card">
                <div class="rate-limit-card__name">{{ key }}</div>
                <div class="rate-limit-card__numbers">
                  <span class="rate-limit-card__remaining">{{ rl.remaining.toLocaleString() }}</span>
                  <span class="rate-limit-card__of"> / {{ rl.limit.toLocaleString() }}</span>
                </div>
                <div class="rate-limit-card__bar-track">
                  <div class="rate-limit-card__bar-fill" :style="{ width: `${ratePct(rl)}%`, backgroundColor: rateVariant(rl) === 'failed' ? 'var(--color-error)' : rateVariant(rl) === 'warning' ? 'var(--color-warning)' : 'var(--color-success)' }" />
                </div>
                <div class="rate-limit-card__meta">
                  <AppBadge :variant="rateVariant(rl)">{{ ratePct(rl) }}% remaining</AppBadge>
                  <span v-if="rl.reset_at" class="rate-limit-card__reset">Resets {{ resetAt(rl.reset_at) }}</span>
                </div>
              </div>
            </AppCard>
          </div>
          <LoadingSpinner v-else-if="rateLimitLoading" label="Fetching rate limit…" />
        </div>

        <!-- Watched Repos (superuser only) -->
        <div v-if="isSuperuser" class="panel" style="margin-top:1.5rem">
          <p class="panel__title">Watched Repos</p>
          <p class="panel__subtitle" style="margin-bottom:1rem">Watched repos are re-analyzed daily to keep their data fresh.</p>

          <div v-if="watchedError" class="empty-state">{{ watchedError }}</div>
          <LoadingSpinner v-else-if="watchedLoading" label="Loading…" />

          <div v-else-if="watchedRepos.length > 0" style="margin-bottom:1rem">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Repo</th>
                  <th>Last Analyzed</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="repo in watchedRepos" :key="repo.id">
                  <td>
                    <a :href="repo.url" target="_blank" rel="noopener noreferrer" class="table-link">
                      {{ repo.owner }}/{{ repo.name }}
                    </a>
                  </td>
                  <td>{{ repo.last_analyzed_at ? new Date(repo.last_analyzed_at).toLocaleDateString() : '—' }}</td>
                  <td>
                    <AppBadge :variant="repo.is_stale ? 'warning' : 'completed'">
                      {{ repo.is_stale ? 'Stale' : 'Fresh' }}
                    </AppBadge>
                  </td>
                  <td>
                    <AppButton variant="secondary" @click="unwatch(repo.id)" style="font-size:0.75rem;padding:2px 8px">
                      Unwatch
                    </AppButton>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-state" style="padding:1rem 0">No watched repos yet.</div>

          <!-- Search to add -->
          <div class="watched-search">
            <p style="font-weight:500;margin-bottom:0.5rem;font-size:0.875rem">Add a repo to watch:</p>
            <div class="watched-search__input-wrap">
              <input
                v-model="watchSearchQuery"
                class="table-search watched-search__input"
                placeholder="Type to search analyzed repos…"
                autocomplete="off"
                @input="onWatchSearchInput"
                @keydown.escape="clearWatchSearch"
              />
              <span v-if="watchSearchLoading" class="watched-search__spinner spinner spinner--sm" />
              <button v-else-if="watchSearchQuery" class="watched-search__clear" @click="clearWatchSearch">✕</button>

              <div v-if="watchSearchResults.length > 0" class="watched-search__dropdown">
                <div
                  v-for="repo in watchSearchResults"
                  :key="repo.id"
                  class="watched-search__option"
                  @click="watch(repo); clearWatchSearch()"
                >
                  <span class="watched-search__option-name">{{ repo.owner }}/{{ repo.name }}</span>
                  <span class="watched-search__option-url">{{ repo.url }}</span>
                </div>
              </div>

              <div v-else-if="watchSearchQuery.trim() && !watchSearchLoading && watchSearchResults.length === 0" class="watched-search__dropdown">
                <div class="watched-search__empty">No unmatched repos found</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Repo of the Week (superuser only) -->
        <div v-if="isSuperuser" class="panel" style="margin-top:1.5rem">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem">
            <div>
              <p class="panel__title" style="margin:0">Repo of the Week</p>
              <p class="panel__subtitle" style="margin:0.25rem 0 0">
                Picks a public repo for the home page spotlight. Replaces this week's pick if one exists.
              </p>
            </div>
            <AppButton variant="primary" :loading="spotlightLoading" @click="pickSpotlight">
              {{ spotlightLoading ? 'Picking…' : 'Pick Now' }}
            </AppButton>
          </div>
          <div v-if="spotlightError" class="empty-state" style="padding:0.5rem 0;color:var(--color-error)">
            {{ spotlightError }}
          </div>
          <div v-if="spotlightResult" style="display:flex;align-items:center;gap:0.75rem;padding:0.75rem;background:var(--color-surface);border:1px solid var(--color-border);border-radius:6px">
            <AppBadge variant="completed">Selected</AppBadge>
            <a :href="spotlightResult.url" target="_blank" rel="noopener noreferrer" class="table-link" style="font-weight:600">
              {{ spotlightResult.owner }}/{{ spotlightResult.name }}
            </a>
            <span style="color:var(--color-text-muted);font-size:0.8125rem">
              week of {{ spotlightResult.week_start }} · pick #{{ spotlightResult.pick_number }}
            </span>
          </div>
        </div>

        <div style="margin-top:1.5rem">
          <AppButton variant="secondary" :disabled="loading" @click="fetchStats">
            Refresh All
          </AppButton>
        </div>
      </template>
    </div>
  </div>
</template>
