<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface MonthEntry { month: string; count: number }

export interface FilterSelection { year: string; months: Set<number>; days: Set<number> }

const props = defineProps<{
  data: MonthEntry[]
  // "YYYY-MM" → sorted list of day numbers that have commits
  dayData?: Record<string, number[]>
}>()
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
const selectedDays = ref<Set<number>>(new Set())

watch(selectedYear, () => {
  selectedMonths.value = new Set()
  selectedDays.value = new Set()
})
watch(selectedMonths, () => { selectedDays.value = new Set() })

const availableMonths = computed(() => {
  if (selectedYear.value === 'All') return new Set<number>()
  const set = new Set<number>()
  props.data.forEach(d => {
    if (d.month.startsWith(selectedYear.value)) set.add(parseInt(d.month.slice(5, 7)))
  })
  return set
})

// Days available: union of days across all selected months (or single active month)
const availableDays = computed<number[]>(() => {
  if (!props.dayData || selectedYear.value === 'All') return []
  const activeMos = selectedMonths.value.size > 0
    ? Array.from(selectedMonths.value)
    : Array.from(availableMonths.value)
  if (activeMos.length !== 1) return []  // only show days when exactly one month is active
  const moKey = `${selectedYear.value}-${String(activeMos[0]).padStart(2, '0')}`
  return props.dayData[moKey] ?? []
})

function toggleMonth(m: number) {
  const next = new Set(selectedMonths.value)
  if (next.has(m)) next.delete(m)
  else next.add(m)
  selectedMonths.value = next
}

function toggleDay(d: number) {
  const next = new Set(selectedDays.value)
  if (next.has(d)) next.delete(d)
  else next.add(d)
  selectedDays.value = next
}

const filtered = computed(() => {
  let result = props.data
  if (selectedYear.value !== 'All') result = result.filter(d => d.month.startsWith(selectedYear.value))
  if (selectedMonths.value.size > 0) result = result.filter(d => selectedMonths.value.has(parseInt(d.month.slice(5, 7))))
  return result
})

watch(filtered, () => {
  emit('update:filtered', filtered.value)
  emit('change', { year: selectedYear.value, months: selectedMonths.value, days: selectedDays.value })
}, { immediate: true })

watch(selectedDays, () => {
  emit('change', { year: selectedYear.value, months: selectedMonths.value, days: selectedDays.value })
})
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

    <div v-if="availableDays.length" class="tl-filter__row">
      <span class="tl-filter__label">Day</span>
      <div class="tl-filter__chips tl-filter__chips--days">
        <button
          v-for="d in availableDays"
          :key="d"
          class="tl-filter__chip tl-filter__chip--day"
          :class="{ 'tl-filter__chip--active': selectedDays.has(d) }"
          @click="toggleDay(d)"
        >{{ d }}</button>
      </div>
    </div>
  </div>
</template>
