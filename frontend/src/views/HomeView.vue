<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import URLInputForm from '../components/analysis/URLInputForm.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import AppButton from '../components/ui/AppButton.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'
import CompareModal from '../components/ui/CompareModal.vue'
import { useAnalysisStore } from '../stores/analysis'
import type { RunListItem } from '../stores/analysis'

const router = useRouter()
const store = useAnalysisStore()

async function handleSubmit(url: string) {
  try {
    const runId = await store.submitUrl(url)
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

function togglePin(repoUrl: string) {
  const w = new Set(watchlist.value)
  if (w.has(repoUrl)) w.delete(repoUrl)
  else w.add(repoUrl)
  watchlist.value = w
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify([...w]))
}

const pinnedItems = computed(() => items.value.filter(r => watchlist.value.has(r.repo_url)))
const unpinnedItems = computed(() => items.value.filter(r => !watchlist.value.has(r.repo_url)))

</script>

<template>
  <div>
    <main class="hero hero--compact">
      <h1 class="hero__title">Atlas <span>Insight</span></h1>
      <p class="hero__subtitle">
        Submit any public GitHub repository and get a deep analysis of its commit history,
        architecture, dependencies, and health signals.
      </p>
      <URLInputForm
        :loading="store.status === 'submitting'"
        :error="store.error"
        @submitted="handleSubmit"
      />
    </main>

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
