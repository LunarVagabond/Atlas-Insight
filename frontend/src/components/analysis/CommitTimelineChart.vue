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
import type { CommitData, MonthlyCommit } from '../../stores/analysis'
import TimelineFilter, { type FilterSelection } from './TimelineFilter.vue'
import CommitMonthDrawer from './CommitMonthDrawer.vue'
import { useTableFilter } from '../../composables/useTableFilter'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps<{ commits: CommitData; repoUrl?: string }>()

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

const churnFilter = useTableFilter(
  filteredChurn as unknown as import('vue').Ref<Record<string, unknown>[]>,
  ['month'],
  'month',
  'desc',
)

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

const activeMonth = ref<string | null>(null)
const activeMonthCommits = computed<MonthlyCommit[]>(() =>
  activeMonth.value ? (props.commits.monthly_commits?.[activeMonth.value] ?? []) : []
)

function openMonth(month: string) {
  activeMonth.value = month
}

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
      <input
        v-model="churnFilter.query.value"
        class="table-search"
        placeholder="Search by month…"
      />
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="churnFilter.setSort('month')">
              Month {{ churnFilter.sortIcon('month') }}
            </th>
            <th class="runs-table__sortable" @click="churnFilter.setSort('active')">
              Active {{ churnFilter.sortIcon('active') }}
            </th>
            <th class="runs-table__sortable" @click="churnFilter.setSort('new')">
              New {{ churnFilter.sortIcon('new') }}
            </th>
            <th class="runs-table__sortable" @click="churnFilter.setSort('lost')">
              Lost {{ churnFilter.sortIcon('lost') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in (churnFilter.filtered.value as any[])"
            :key="row.month"
            class="churn-row"
            :class="{ 'churn-row--clickable': commits.monthly_commits?.[row.month]?.length }"
            @click="commits.monthly_commits?.[row.month]?.length && openMonth(row.month)"
          >
            <td class="churn-row__month">
              {{ row.month }}
              <span v-if="commits.monthly_commits?.[row.month]?.length" class="churn-row__hint">↗</span>
            </td>
            <td>{{ row.active }}</td>
            <td style="color: var(--color-success)">+{{ row.new }}</td>
            <td style="color: var(--color-error)">-{{ row.lost }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!churnFilter.filtered.value.length" class="empty-state" style="margin-top:1rem">No contributor data for selected range</div>
    </div>
  </div>

  <CommitMonthDrawer
    :month="activeMonth"
    :commits="activeMonthCommits"
    :repo-url="repoUrl"
    @close="activeMonth = null"
  />
</template>
