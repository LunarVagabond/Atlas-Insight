<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface MonthEntry { month: string; count: number }

export interface FilterSelection { year: string; months: Set<number> }

const props = defineProps<{ data: MonthEntry[] }>()
const emit = defineEmits<{
  (e: 'update:filtered', val: MonthEntry[]): void
  (e: 'change', val: FilterSelection): void
}>()

const MONTH_LABELS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

const years = computed(() => {
  const set = new Set(props.data.map(d => d.month.slice(0, 4)))
  return ['All', ...Array.from(set).sort()]
})

const selectedYear = ref('All')
const selectedMonths = ref<Set<number>>(new Set())

watch(selectedYear, () => { selectedMonths.value = new Set() })

const availableMonths = computed(() => {
  if (selectedYear.value === 'All') return new Set<number>()
  const set = new Set<number>()
  props.data.forEach(d => {
    if (d.month.startsWith(selectedYear.value)) set.add(parseInt(d.month.slice(5, 7)))
  })
  return set
})

function toggleMonth(m: number) {
  const next = new Set(selectedMonths.value)
  if (next.has(m)) next.delete(m)
  else next.add(m)
  selectedMonths.value = next
}

const filtered = computed(() => {
  let result = props.data
  if (selectedYear.value !== 'All') result = result.filter(d => d.month.startsWith(selectedYear.value))
  if (selectedMonths.value.size > 0) result = result.filter(d => selectedMonths.value.has(parseInt(d.month.slice(5, 7))))
  return result
})

watch(filtered, (v) => {
  emit('update:filtered', v)
  emit('change', { year: selectedYear.value, months: selectedMonths.value })
}, { immediate: true })
</script>

<template>
  <div class="tl-filter">
    <div class="tl-filter__row">
      <span class="tl-filter__label">Year</span>
      <div class="tl-filter__chips">
        <button
          v-for="y in years"
          :key="y"
          class="tl-filter__chip"
          :class="{ 'tl-filter__chip--active': selectedYear === y }"
          @click="selectedYear = y"
        >{{ y }}</button>
      </div>
    </div>

    <div v-if="selectedYear !== 'All'" class="tl-filter__row">
      <span class="tl-filter__label">Month</span>
      <div class="tl-filter__chips">
        <button
          v-for="(label, idx) in MONTH_LABELS"
          :key="idx"
          class="tl-filter__chip"
          :class="{
            'tl-filter__chip--active': selectedMonths.has(idx + 1),
            'tl-filter__chip--disabled': !availableMonths.has(idx + 1),
          }"
          :disabled="!availableMonths.has(idx + 1)"
          @click="toggleMonth(idx + 1)"
        >{{ label }}</button>
      </div>
    </div>
  </div>
</template>
