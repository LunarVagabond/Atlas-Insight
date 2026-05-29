<script setup lang="ts">
import { computed } from 'vue'
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

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps<{ commits: CommitData }>()

const chartData = computed(() => ({
  labels: props.commits.monthly_frequency.map(d => d.month),
  datasets: [
    {
      label: 'Commits per Month',
      data: props.commits.monthly_frequency.map(d => d.count),
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
    x: {
      ticks: { maxTicksLimit: 12 },
      grid: { display: false },
    },
    y: {
      beginAtZero: true,
      ticks: { precision: 0 },
    },
  },
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Commit Timeline</h2>
    <div v-if="commits.monthly_frequency.length" class="chart-wrapper">
      <Line :data="chartData" :options="chartOptions" />
    </div>
    <div v-else class="empty-state">No commit data available</div>

    <div v-if="commits.contributor_churn.length" style="margin-top: 2rem">
      <h3 class="panel__title">Contributor Activity</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Month</th>
            <th>Active</th>
            <th>New</th>
            <th>Lost</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in commits.contributor_churn.slice(-12)" :key="row.month">
            <td>{{ row.month }}</td>
            <td>{{ row.active }}</td>
            <td style="color: var(--color-success)">+{{ row.new }}</td>
            <td style="color: var(--color-error)">-{{ row.lost }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
