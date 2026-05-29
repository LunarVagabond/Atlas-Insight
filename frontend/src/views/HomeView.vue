<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import URLInputForm from '../components/analysis/URLInputForm.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import AppButton from '../components/ui/AppButton.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'
import { useAnalysisStore } from '../stores/analysis'
import type { RunListItem } from '../stores/analysis'

const router = useRouter()
const store = useAnalysisStore()

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
const selectedIds = ref<Set<string>>(new Set())
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

function toggleSelect(id: string) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else if (s.size < 2) s.add(id)
  selectedIds.value = s
}

function goToCompare() {
  const [a, b] = [...selectedIds.value]
  router.push(`/compare?a=${a}&b=${b}`)
}
</script>

<template>
  <div>
    <main class="hero hero--compact">
      <h1 class="hero__title">Repository <span>Archaeology</span></h1>
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
          <AppButton v-if="selectedIds.size === 2" variant="primary" @click="goToCompare">
            Compare ({{ selectedIds.size }})
          </AppButton>
          <span v-else-if="selectedIds.size === 1" class="home-runs__compare-hint">
            Select 1 more to compare
          </span>
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
            <tr
              v-for="run in items"
              :key="run.id"
              class="runs-table__row"
              @click="goToRun(run.id)"
            >
              <td @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedIds.has(run.id)"
                  :disabled="!selectedIds.has(run.id) && selectedIds.size >= 2"
                  @change="toggleSelect(run.id)"
                  style="cursor:pointer"
                />
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
                <AppButton variant="secondary" @click.stop="goToRun(run.id)" style="font-size:0.8125rem;padding:4px 12px">
                  View
                </AppButton>
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
