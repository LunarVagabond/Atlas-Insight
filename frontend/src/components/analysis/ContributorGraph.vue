<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import type { CommitData } from '../../stores/analysis'
import type { FilterSelection } from './TimelineFilter.vue'
import { isFilterActive, monthInFilter } from '../../composables/timelineFilterUtils'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = withDefaults(defineProps<{
  commits: CommitData
  selection?: FilterSelection
}>(), {
  selection: () => ({ year: 'All', months: new Set(), days: new Set() }),
})

// Build per-author monthly commit counts from monthly_frequency + monthly_commits
const PALETTE = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#3b82f6',
  '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316',
]

const chartData = computed(() => {
  const monthly = props.commits.monthly_commits
  if (!monthly || Object.keys(monthly).length === 0) return null

  // Collect all months in order
  const months = Object.keys(monthly).sort()
  let displayMonths = months.slice(-18)
  if (isFilterActive(props.selection)) {
    displayMonths = displayMonths.filter(m => monthInFilter(m, props.selection))
  }
  if (!displayMonths.length) return null

  // Collect all authors across those months
  const authorCounts: Record<string, Record<string, number>> = {}
  for (const month of displayMonths) {
    const commits = monthly[month] ?? []
    for (const c of commits) {
      const author = c.author || 'Unknown'
      if (!authorCounts[author]) authorCounts[author] = {}
      authorCounts[author][month] = (authorCounts[author][month] ?? 0) + 1
    }
  }

  // Top 8 authors by total commits
  const authorTotals = Object.entries(authorCounts)
    .map(([author, months]) => ({ author, total: Object.values(months).reduce((a, b) => a + b, 0) }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 8)

  const datasets = authorTotals.map(({ author }, i) => ({
    label: author.length > 20 ? author.slice(0, 18) + '…' : author,
    data: displayMonths.map(m => authorCounts[author][m] ?? 0),
    backgroundColor: PALETTE[i % PALETTE.length],
    borderRadius: 2,
  }))

  return {
    labels: displayMonths.map(m => {
      const [year, month] = m.split('-')
      return new Date(+year, +month - 1).toLocaleString('default', { month: 'short', year: '2-digit' })
    }),
    datasets,
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const, labels: { boxWidth: 12, font: { size: 11 } } },
    title: { display: false },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } },
    y: { stacked: true, beginAtZero: true, ticks: { precision: 0, font: { size: 10 } } },
  },
}
</script>

<template>
  <div v-if="chartData" class="contributor-graph">
    <h3 class="contributor-graph__title">Contributor Activity</h3>
    <p class="contributor-graph__subtitle">Monthly commits per author (last 18 months, top 8 contributors)</p>
    <div class="contributor-graph__chart">
      <Bar :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>
