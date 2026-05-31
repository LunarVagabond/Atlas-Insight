<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import AppBadge from '../components/ui/AppBadge.vue'
import AppButton from '../components/ui/AppButton.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'
import CompareModal from '../components/ui/CompareModal.vue'
import type { RunListItem } from '../stores/analysis'

const router = useRouter()

const q = ref('')
const tagQ = ref('')
const sort = ref<'triggered_at' | 'completed_at' | 'status'>('triggered_at')
const order = ref<'desc' | 'asc'>('desc')
const page = ref(1)
const perPage = 25
const showCompareModal = ref(false)

const items = ref<RunListItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

async function fetchRuns() {
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get('/api/v1/repositories/runs/', {
      params: { q: q.value, sort: sort.value, order: order.value, page: page.value, per_page: perPage },
    })
    items.value = data.items
    total.value = data.total
  } catch {
    error.value = 'Failed to load runs'
  } finally {
    loading.value = false
  }
}

onMounted(fetchRuns)
watch([q, sort, order], () => { page.value = 1; fetchRuns() })
watch(page, fetchRuns)

const totalPages = computed(() => Math.ceil(total.value / perPage))

const activeTag = ref<string | null>(null)
const showTagDropdown = ref(false)

const allTags = computed(() => {
  const tags = new Set<string>()
  items.value.forEach(r => r.tags?.forEach(t => tags.add(t)))
  return [...tags].sort()
})

const tagSuggestions = computed(() => {
  const needle = tagQ.value.toLowerCase().trim()
  if (!needle) return allTags.value
  return allTags.value.filter(t => t.toLowerCase().includes(needle))
})

function selectTag(tag: string) {
  activeTag.value = tag
  tagQ.value = ''
  showTagDropdown.value = false
}

function clearTag() {
  activeTag.value = null
  tagQ.value = ''
}

function onTagFocus() {
  showTagDropdown.value = true
}

function onTagBlur() {
  setTimeout(() => { showTagDropdown.value = false }, 150)
}

const filteredItems = computed(() =>
  activeTag.value ? items.value.filter(r => r.tags?.includes(activeTag.value!)) : items.value
)

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
</script>

<template>
  <div class="results-layout">
    <div class="results-layout__header">
      <div class="results-header">
        <h1 class="results-header__title">All Runs</h1>
        <RouterLink to="/" class="btn btn--secondary" style="font-size:0.875rem">
          + New Analysis
        </RouterLink>
      </div>

      <div class="runs-search">
        <input
          v-model="q"
          class="url-form__input runs-search__text-input"
          placeholder="Search by URL, project, or author…"
        />

        <div class="runs-search__tag-wrap">
          <div class="runs-search__tag-field">
            <span v-if="activeTag" class="runs-search__tag-chip">
              {{ activeTag }}
              <button class="runs-search__tag-chip-remove" @click="clearTag" aria-label="Remove tag filter">×</button>
            </span>
            <input
              v-model="tagQ"
              class="runs-search__tag-input"
              placeholder="Filter by tag…"
              @focus="onTagFocus"
              @blur="onTagBlur"
            />
          </div>
          <div v-if="showTagDropdown && tagSuggestions.length" class="runs-search__tag-dropdown">
            <button
              v-for="tag in tagSuggestions"
              :key="tag"
              class="runs-search__tag-option"
              @mousedown.prevent="selectTag(tag)"
            >{{ tag }}</button>
          </div>
        </div>

        <span class="runs-search__count">{{ total }} repo{{ total !== 1 ? 's' : '' }}</span>
        <AppButton variant="secondary" @click="showCompareModal = true" style="margin-left:1rem">
          Compare
        </AppButton>
      </div>
    </div>

    <div class="results-layout__content">
      <LoadingSpinner v-if="loading" label="Loading runs…" />

      <div v-else-if="error" class="empty-state">{{ error }}</div>

      <div v-else-if="!items.length" class="empty-state">
        No runs found{{ q ? ` matching "${q}"` : '' }}.
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
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in filteredItems"
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

  <CompareModal v-if="showCompareModal" @close="showCompareModal = false" />
</template>
