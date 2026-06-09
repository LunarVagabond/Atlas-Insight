<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  branches: string[]
  modelValue: string
  loading?: boolean
  scanned?: string[]
  defaultBranch?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [branch: string]
}>()

const open = ref(false)
const filter = ref('')
const rootEl = ref<HTMLElement | null>(null)

const sorted = computed(() => {
  const db = props.defaultBranch
  if (!db) return props.branches
  return [db, ...props.branches.filter(b => b !== db)]
})

const filtered = computed(() => {
  const base = sorted.value
  if (!filter.value) return base
  const q = filter.value.toLowerCase()
  return base.filter(b => b.toLowerCase().includes(q))
})

const scannedSet = computed(() => {
  const s = new Set(props.scanned ?? [])
  // Default branch stored as '' in DB — map to display name so the chip shows correctly
  if (props.defaultBranch && s.has('')) s.add(props.defaultBranch)
  return s
})

const displayValue = computed(() => {
  if (props.modelValue) return props.modelValue
  return props.defaultBranch ?? '(default)'
})

function select(branch: string) {
  // Default branch is stored as '' — normalize so consumers don't need to know
  const val = (props.defaultBranch && branch === props.defaultBranch) ? '' : branch
  emit('update:modelValue', val)
  open.value = false
  filter.value = ''
}

function toggle() {
  if (props.loading) return
  open.value = !open.value
  if (open.value) filter.value = ''
}

function onClickOutside(e: MouseEvent) {
  if (rootEl.value && !rootEl.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div ref="rootEl" class="branch-select" :class="{ 'branch-select--open': open }">
    <button
      type="button"
      class="branch-select__trigger"
      :disabled="loading"
      @click="toggle"
      :title="modelValue ? `Branch: ${modelValue}` : 'Default branch'"
    >
      <svg class="branch-select__icon" width="13" height="13" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        <path d="M11.75 2.5a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0zm.75 2.25a2.25 2.25 0 1 1 0-4.5 2.25 2.25 0 0 1 0 4.5zM4.25 2.5a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0zM5 4.75a2.25 2.25 0 1 1 0-4.5 2.25 2.25 0 0 1 0 4.5zM4.25 13.5a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0zM5 15.75a2.25 2.25 0 1 1 0-4.5 2.25 2.25 0 0 1 0 4.5zm-1-11v4.505c0 .17.1.32.26.39l3.5 1.5a.75.75 0 0 0 .59 0l3.5-1.5a.43.43 0 0 0 .26-.39V4.75a2.22 2.22 0 0 1-1.5 0v4.09l-2.75 1.18L5.5 8.84V4.75a2.22 2.22 0 0 1-1.5 0z"/>
      </svg>
      <span class="branch-select__label">{{ displayValue }}</span>
      <svg class="branch-select__caret" width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true">
        <path d="M1 3l4 4 4-4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div v-if="open" class="branch-select__dropdown">
      <div class="branch-select__search">
        <input
          v-model="filter"
          type="text"
          class="branch-select__input"
          placeholder="Filter branches…"
          autofocus
        />
      </div>
      <ul class="branch-select__list" role="listbox">
        <li
          v-for="b in filtered"
          :key="b"
          class="branch-select__item"
          :class="{ 'branch-select__item--active': b === modelValue || (!modelValue && b === (defaultBranch ?? branches[0])) }"
          role="option"
          :aria-selected="b === modelValue"
          :title="!modelValue && b === defaultBranch ? 'Already analyzing this branch' : undefined"
          @click="select(b)"
        >
          <span class="branch-select__item-name">{{ b }}</span>
          <span v-if="b === defaultBranch" class="branch-select__default-chip">Default</span>
          <span v-if="scannedSet.has(b)" class="branch-select__scanned-chip">Scanned</span>
          <span v-else class="branch-select__unscanned-chip">Not scanned</span>
        </li>
        <li v-if="filtered.length === 0" class="branch-select__empty">No matches</li>
      </ul>
    </div>
  </div>
</template>
