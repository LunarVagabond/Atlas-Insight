<script setup lang="ts">
import { computed, ref } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import type { CommitData } from '../../stores/analysis'
import TimelineFilter, { type FilterSelection } from './TimelineFilter.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps<{ commits: CommitData }>()

const filteredMonthly = ref<{ month: string; count: number }[]>([])
const selection = ref<FilterSelection>({ year: 'All', months: new Set() })

function onFilterChange(sel: FilterSelection) {
  selection.value = sel
}

const filteredChurn = computed(() => {
  let rows = props.commits.contributor_churn
  if (selection.value.year !== 'All') {
    rows = rows.filter(r => r.month.startsWith(selection.value.year))
  }
  if (selection.value.months.size > 0) {
    rows = rows.filter(r => selection.value.months.has(parseInt(r.month.slice(5, 7))))
  }
  return rows
})

const chartData = computed(() => ({
  labels: filteredMonthly.value.map(d => d.month),
  datasets: [
    {
      label: 'Commits',
      data: filteredMonthly.value.map(d => d.count),
      borderColor: '#0969da',
      backgroundColor: 'rgba(9, 105, 218, 0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { ticks: { maxTicksLimit: 14 }, grid: { display: false } },
    y: { beginAtZero: true, ticks: { precision: 0 } },
  },
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Commit Timeline</h2>

    <div v-if="commits.monthly_frequency.length">
      <TimelineFilter
        :data="commits.monthly_frequency"
        @update:filtered="filteredMonthly = $event"
        @change="onFilterChange"
      />
      <div class="chart-wrapper" style="margin-top: 1rem">
        <Line v-if="filteredMonthly.length" :data="chartData" :options="chartOptions" />
        <div v-else class="empty-state">No data for selected range</div>
      </div>
    </div>
    <div v-else class="empty-state">No commit data available</div>

    <div v-if="commits.contributor_churn.length" style="margin-top: 2rem">
      <h3 class="panel__title">Contributor Activity</h3>
      <table class="data-table">
        <thead>
          <tr><th>Month</th><th>Active</th><th>New</th><th>Lost</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredChurn" :key="row.month">
            <td>{{ row.month }}</td>
            <td>{{ row.active }}</td>
            <td style="color: var(--color-success)">+{{ row.new }}</td>
            <td style="color: var(--color-error)">-{{ row.lost }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filteredChurn.length" class="empty-state" style="margin-top:1rem">No contributor data for selected range</div>
    </div>
  </div>
</template>
