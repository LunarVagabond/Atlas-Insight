<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import type { RunListItem } from '../../stores/analysis'
import AppButton from './AppButton.vue'
import AppBadge from './AppBadge.vue'

const emit = defineEmits<{ close: [] }>()
const router = useRouter()

const q = ref('')
const items = ref<RunListItem[]>([])
const loading = ref(true)
const selected = ref<RunListItem[]>([])

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/repositories/runs/', {
      params: { per_page: 100, sort: 'triggered_at', order: 'desc' },
    })
    items.value = data.items.filter((r: RunListItem) => r.status === 'completed')
  } finally {
    loading.value = false
  }
})

const filtered = computed(() =>
  q.value
    ? items.value.filter(r =>
        r.repo_name.toLowerCase().includes(q.value.toLowerCase()) ||
        r.repo_owner.toLowerCase().includes(q.value.toLowerCase()),
      )
    : items.value,
)

function selectionIndex(id: string) {
  return selected.value.findIndex(r => r.id === id)
}

function toggle(run: RunListItem) {
  const idx = selectionIndex(run.id)
  if (idx !== -1) {
    selected.value = selected.value.filter(r => r.id !== run.id)
  } else if (selected.value.length < 2) {
    selected.value = [...selected.value, run]
  }
}

function compare() {
  const [a, b] = selected.value
  emit('close')
  router.push(`/compare?a=${a.id}&b=${b.id}`)
}
</script>

<template>
  <div class="compare-modal-overlay" @click.self="emit('close')">
    <div class="compare-modal" role="dialog" aria-modal="true">

      <div class="compare-modal__header">
        <div>
          <h2 class="compare-modal__title">Compare Repositories</h2>
          <p class="compare-modal__subtitle">
            Pick two repos to find out which is the better fit for your next open-source contribution.
          </p>
        </div>
        <button class="compare-modal__close" @click="emit('close')" aria-label="Close">✕</button>
      </div>

      <div class="compare-modal__slots">
        <div class="compare-modal__slot" :class="{ 'compare-modal__slot--filled': selected[0] }">
          <span class="compare-modal__slot-label">Repo A</span>
          <span v-if="selected[0]" class="compare-modal__slot-name">{{ selected[0].repo_owner }}/{{ selected[0].repo_name }}</span>
          <span v-else class="compare-modal__slot-empty">Pick from list below</span>
        </div>
        <span class="compare-modal__vs">vs</span>
        <div class="compare-modal__slot" :class="{ 'compare-modal__slot--filled': selected[1] }">
          <span class="compare-modal__slot-label">Repo B</span>
          <span v-if="selected[1]" class="compare-modal__slot-name">{{ selected[1].repo_owner }}/{{ selected[1].repo_name }}</span>
          <span v-else class="compare-modal__slot-empty">Pick from list below</span>
        </div>
      </div>

      <div class="compare-modal__search">
        <input
          v-model="q"
          class="url-form__input"
          placeholder="Filter repositories…"
          autofocus
        />
      </div>

      <div class="compare-modal__list">
        <div v-if="loading" class="compare-modal__empty">Loading…</div>
        <div v-else-if="!filtered.length" class="compare-modal__empty">No completed analyses found.</div>

        <button
          v-for="run in filtered"
          :key="run.id"
          class="compare-modal__item"
          :class="{
            'compare-modal__item--selected': selectionIndex(run.id) !== -1,
            'compare-modal__item--disabled': selectionIndex(run.id) === -1 && selected.length >= 2,
          }"
          @click="toggle(run)"
        >
          <span
            v-if="selectionIndex(run.id) !== -1"
            class="compare-modal__item-badge"
          >{{ selectionIndex(run.id) === 0 ? 'A' : 'B' }}</span>
          <span v-else class="compare-modal__item-badge compare-modal__item-badge--empty"></span>

          <span class="compare-modal__item-info">
            <span class="compare-modal__item-name">{{ run.repo_owner }}/{{ run.repo_name }}</span>
            <span class="compare-modal__item-url">{{ run.repo_url }}</span>
          </span>

          <AppBadge v-if="run.is_stale" variant="warning" style="margin-left:auto;flex-shrink:0">Stale</AppBadge>
        </button>
      </div>

      <div class="compare-modal__footer">
        <AppButton variant="secondary" @click="emit('close')">Cancel</AppButton>
        <AppButton variant="primary" :disabled="selected.length < 2" @click="compare">
          Compare{{ selected.length === 2 ? ` ${selected[0].repo_name} vs ${selected[1].repo_name}` : '' }}
        </AppButton>
      </div>

    </div>
  </div>
</template>
