<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import AppBadge from '../components/ui/AppBadge.vue'
import AppButton from '../components/ui/AppButton.vue'
import SkeletonCard from '../components/ui/SkeletonCard.vue'
import { useAnalysisStore } from '../stores/analysis'
import { useAuthStore } from '../stores/auth'
import { EXTERNAL_IMG_ATTRS } from '../utils/externalImage'
import type { RunListItem } from '../stores/analysis'

const router = useRouter()
const store = useAnalysisStore()
const authStore = useAuthStore()

const q = ref('')
const sort = ref<'triggered_at' | 'completed_at' | 'status'>('triggered_at')
const order = ref<'desc' | 'asc'>('desc')
const page = ref(1)
const perPage = 25

const items = ref<RunListItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

async function fetchRuns() {
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get('/api/v1/repositories/runs/', {
      params: { q: q.value, sort: sort.value, order: order.value, page: page.value, per_page: perPage, mine: true },
    })
    items.value = data.items
    total.value = data.total
  } catch {
    error.value = 'Failed to load runs'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    router.push('/')
    return
  }
  await fetchRuns()
})

watch([q, sort, order], () => { page.value = 1; fetchRuns() })
watch(page, fetchRuns)

const totalPages = computed(() => Math.ceil(total.value / perPage))

function setSort(field: typeof sort.value) {
  if (sort.value === field) {
    order.value = order.value === 'desc' ? 'asc' : 'desc'
  } else {
    sort.value = field
    order.value = 'desc'
  }
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

async function handleReanalyze(run: RunListItem) {
  try {
    const newId = await store.retryRun(run.id)
    router.push(`/results/${newId}`)
  } catch {
    error.value = 'Failed to re-analyze. Please try again.'
  }
}

async function handleDelete(run: RunListItem) {
  if (!window.confirm('Delete this run? This cannot be undone.')) return
  try {
    await store.deleteRun(run.id)
    items.value = items.value.filter(r => r.id !== run.id)
    total.value = Math.max(0, total.value - 1)
  } catch {
    error.value = 'Failed to delete run. Please try again.'
  }
}
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <!-- User header -->
      <div class="dashboard-header">
        <img
          v-if="authStore.user?.avatar_url"
          :src="authStore.user.avatar_url"
          :alt="authStore.displayName"
          class="dashboard-header__avatar"
          v-bind="EXTERNAL_IMG_ATTRS"
        />
        <div class="dashboard-header__info">
          <h1 class="dashboard-header__title">My Analyses</h1>
          <span class="dashboard-header__login">{{ authStore.user?.github_login }}</span>
        </div>
        <RouterLink to="/" class="btn btn--secondary" style="font-size:0.875rem;margin-left:auto">
          + New Analysis
        </RouterLink>
      </div>

      <div class="runs-search" style="margin-top:1.25rem">
        <input
          v-model="q"
          class="url-form__input"
          placeholder="Search by URL, project name, or author…"
          style="max-width:400px"
        />
        <span class="runs-search__count">{{ total }} repo{{ total !== 1 ? 's' : '' }}</span>
      </div>
    </div>

    <div class="results-layout__content">
      <div v-if="loading" class="runs-skeleton">
        <SkeletonCard v-for="i in 6" :key="i" :show-header="false" :lines="2" />
      </div>

      <div v-else-if="error" class="empty-state">
        <div class="empty-state__icon">⚠️</div>
        <p class="empty-state__title">{{ error }}</p>
        <div class="empty-state__action">
          <AppButton variant="secondary" @click="fetchRuns">Retry</AppButton>
        </div>
      </div>

      <div v-else-if="!items.length" class="empty-state">
        <div class="empty-state__icon">📂</div>
        <p class="empty-state__title">No analyses yet</p>
        <p class="empty-state__desc">Analyze a repository to track it here. Favorites and private repos will appear in your dashboard.</p>
        <div class="empty-state__action">
          <RouterLink to="/" class="btn btn--primary">Analyze a Repository</RouterLink>
        </div>
      </div>

      <template v-else>
        <table class="data-table runs-table">
          <thead>
            <tr>
              <th>Author</th>
              <th>Repository</th>
              <th>Status</th>
              <th class="runs-table__sortable" @click="setSort('triggered_at')">
                Last Scan {{ sortIcon('triggered_at') }}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in items"
              :key="run.id"
              class="runs-table__row"
              @click="goToRun(run.id)"
            >
              <td>
                <span class="runs-table__author">{{ run.repo_owner }}</span>
              </td>
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
                <div class="dashboard-actions" @click.stop>
                  <AppButton
                    variant="secondary"
                    style="font-size:0.8125rem;padding:4px 12px"
                    @click.stop="goToRun(run.id)"
                  >
                    View
                  </AppButton>
                  <AppButton
                    variant="secondary"
                    style="font-size:0.8125rem;padding:4px 12px"
                    @click.stop="handleReanalyze(run)"
                    title="Re-analyze"
                  >
                    ↻
                  </AppButton>
                  <button
                    v-if="run.is_private"
                    class="btn btn--danger"
                    @click.stop="handleDelete(run)"
                    title="Delete run"
                  >
                    Delete
                  </button>
                </div>
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
</template>
