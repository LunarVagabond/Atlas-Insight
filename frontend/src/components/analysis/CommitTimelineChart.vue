<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
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
import type { CommitData, GitHubContributor, MonthlyCommit } from '../../stores/analysis'
import TimelineFilter, { type FilterSelection } from './TimelineFilter.vue'
import CommitMonthDrawer from './CommitMonthDrawer.vue'
import GitGraphSvg, { type GraphRow, type GraphCommit, type MonthSep } from './GitGraphSvg.vue'
import CommitBodyDrawer from './CommitBodyDrawer.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps<{
  commits: CommitData
  repoUrl?: string
  githubContributors?: GitHubContributor[]
}>()

// ── Filter (shared: chart + git log) ─────────────────────────────────────────
const filteredMonthly = ref<{ month: string; count: number }[]>([])
const selection = ref<FilterSelection>({ year: 'All', months: new Set(), days: new Set() })
function onFilterChange(sel: FilterSelection) { selection.value = sel }

// Day data: "YYYY-MM" → sorted unique day numbers from commit dates
const dayData = computed<Record<string, number[]>>(() => {
  const mc = props.commits.monthly_commits ?? {}
  const result: Record<string, number[]> = {}
  for (const [month, commits] of Object.entries(mc)) {
    const days = new Set(commits.map(c => parseInt(c.date.slice(8, 10))))
    result[month] = Array.from(days).sort((a, b) => a - b)
  }
  return result
})

// ── Day-level chart data (when day filter active) ─────────────────────────────
const dayChartData = computed<{ label: string; count: number }[] | null>(() => {
  const sel = selection.value
  if (!sel.days.size || sel.year === 'All') return null
  const mc = props.commits.monthly_commits ?? {}

  // Active month key(s) — only works when exactly one month active
  const activeMos = sel.months.size > 0 ? Array.from(sel.months) : null
  if (!activeMos || activeMos.length !== 1) return null
  const moKey = `${sel.year}-${String(activeMos[0]).padStart(2, '0')}`
  const commits = mc[moKey] ?? []

  const minDay = Math.min(...sel.days)
  const maxDay = Math.max(...sel.days)

  // Build day-level counts for the inclusive range
  const counts = new Map<number, number>()
  for (let d = minDay; d <= maxDay; d++) counts.set(d, 0)
  for (const c of commits) {
    const d = parseInt(c.date.slice(8, 10))
    if (d >= minDay && d <= maxDay) counts.set(d, (counts.get(d) ?? 0) + 1)
  }

  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  const moLabel = MONTH_NAMES[activeMos[0] - 1]
  return Array.from(counts.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([day, count]) => ({ label: `${moLabel} ${day}`, count }))
})

// ── Chart ─────────────────────────────────────────────────────────────────────
const chartData = computed(() => {
  const daily = dayChartData.value
  const labels = daily ? daily.map(d => d.label) : filteredMonthly.value.map(d => d.month)
  const data   = daily ? daily.map(d => d.count) : filteredMonthly.value.map(d => d.count)
  return {
    labels,
    datasets: [{
      label: 'Commits',
      data,
      borderColor: '#0969da',
      backgroundColor: 'rgba(9, 105, 218, 0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: daily ? 5 : 3,
    }],
  }
})
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { mode: 'index' as const, intersect: false } },
  scales: {
    x: { ticks: { maxTicksLimit: 14 }, grid: { display: false } },
    y: { beginAtZero: true, ticks: { precision: 0 } },
  },
}

// ── Month drawer ──────────────────────────────────────────────────────────────
const activeMonth = ref<string | null>(null)
const activeMonthCommits = computed<MonthlyCommit[]>(() =>
  activeMonth.value ? (props.commits.monthly_commits?.[activeMonth.value] ?? []) : []
)

// ── Commit body drawer ────────────────────────────────────────────────────────
const activeCommitBody = ref<GraphCommit | null>(null)

// ── Author palette ────────────────────────────────────────────────────────────
const PALETTE = [
  '#0969da','#7c3aed','#059669','#d97706',
  '#dc2626','#0891b2','#db2777','#65a30d',
  '#ea580c','#4338ca','#0f766e','#b45309',
]

const authorColorMap = computed<Map<string, string>>(() => {
  const map = new Map<string, string>()
  let idx = 0
  const mc = props.commits.monthly_commits ?? {}
  for (const month of Object.keys(mc).sort().reverse()) {
    for (const c of mc[month]) {
      if (!map.has(c.author)) {
        map.set(c.author, PALETTE[idx % PALETTE.length])
        idx++
      }
    }
  }
  return map
})

// ── Filter months from selection ──────────────────────────────────────────────
function monthInFilter(month: string): boolean {
  if (selection.value.year !== 'All' && !month.startsWith(selection.value.year)) return false
  if (selection.value.months.size > 0 && !selection.value.months.has(parseInt(month.slice(5, 7)))) return false
  return true
}

function commitInDayFilter(isoDate: string): boolean {
  if (!selection.value.days.size) return true
  const day = parseInt(isoDate.slice(8, 10))
  const minDay = Math.min(...selection.value.days)
  const maxDay = Math.max(...selection.value.days)
  return day >= minDay && day <= maxDay
}

// ── Contributors (filtered by active date range) ───────────────────────────────
interface ContribEntry {
  name: string
  initials: string
  color: string
  commitCount: number
  avatarUrl?: string
  profileUrl?: string
}

function authorInitials(name: string): string {
  const clean = name.replace(/\[bot\]/, '').trim()
  const parts = clean.split(/[\s._-]+/).filter(Boolean)
  return parts.length >= 2 ? (parts[0][0] + parts[1][0]).toUpperCase() : clean.slice(0, 2).toUpperCase()
}

const contributors = computed<ContribEntry[]>(() => {
  const mc = props.commits.monthly_commits ?? {}
  const counts = new Map<string, number>()
  const filteredActive = selection.value.year !== 'All' || selection.value.months.size > 0 || selection.value.days.size > 0

  for (const [month, commits] of Object.entries(mc)) {
    if (filteredActive && !monthInFilter(month)) continue
    for (const c of commits) {
      if (!commitInDayFilter(c.date)) continue
      counts.set(c.author, (counts.get(c.author) ?? 0) + 1)
    }
  }

  const ghMap = new Map<string, GitHubContributor>()
  for (const g of props.githubContributors ?? []) ghMap.set(g.login, g)

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([name, count]) => {
      const gh = ghMap.get(name) ?? ghMap.get(name.replace(/\[bot\]/, ''))
      return {
        name,
        initials: authorInitials(name),
        color: authorColorMap.value.get(name) ?? '#888',
        commitCount: count,
        avatarUrl: gh?.avatar_url,
        profileUrl: gh?.html_url,
      }
    })
})

// ── Git graph rows (commits + month separators, newest first) ─────────────────
function relativeDate(iso: string): string {
  const diffDays = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (diffDays < 1) return 'today'
  if (diffDays < 7) return `${diffDays}d`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w`
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo`
  return `${Math.floor(diffDays / 365)}y`
}

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
function formatMonthLabel(m: string): string {
  const [year, month] = m.split('-')
  return `${MONTH_NAMES[parseInt(month) - 1]} ${year}`
}

const searchQuery = ref('')
const graphScrollEl = ref<HTMLElement | null>(null)

// Reset scroll to top when filter changes (not search)
watch(selection, () => {
  nextTick(() => { if (graphScrollEl.value) graphScrollEl.value.scrollTop = 0 })
}, { deep: true })

const graphRows = computed<GraphRow[]>(() => {
  const mc = props.commits.monthly_commits
  if (!mc) return []

  const q = searchQuery.value.trim().toLowerCase()
  const rows: GraphRow[] = []

  const sortedMonths = Object.keys(mc).sort().reverse().slice(0, 36)

  for (const month of sortedMonths) {
    if (!monthInFilter(month)) continue
    const raw = mc[month]
    if (!raw?.length) continue

    const commits = raw
      .filter(c => commitInDayFilter(c.date))
      .filter(c => !q || c.message.toLowerCase().includes(q) || c.author.toLowerCase().includes(q) || c.sha.startsWith(q))
      .map(c => ({
        sha: c.sha,
        parents: c.parents ?? [],
        message: c.message,
        body: c.body ?? null,
        author: c.author,
        date: c.date,
        color: authorColorMap.value.get(c.author) ?? '#888',
        relativeDate: relativeDate(c.date),
        commitUrl: props.repoUrl ? `${props.repoUrl}/commit/${c.sha}` : null,
      } satisfies GraphCommit))

    if (!commits.length) continue

    const sep: MonthSep = {
      isMonth: true,
      label: formatMonthLabel(month),
      month,
      count: commits.length,
    }

    rows.push(sep, ...commits)
  }

  return rows
})

const totalCommits = computed(() => graphRows.value.filter(r => !(r as MonthSep).isMonth).length)

const commitDateRange = computed<string>(() => {
  const dates = graphRows.value
    .filter(r => !(r as MonthSep).isMonth)
    .map(r => (r as GraphCommit).date)
    .filter(Boolean)
  if (!dates.length) return ''
  const sorted = [...dates].sort()
  const fmt = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  }
  const oldest = fmt(sorted[0])
  const newest = fmt(sorted[sorted.length - 1])
  return oldest === newest ? oldest : `${oldest} – ${newest}`
})
</script>

<template>
  <div class="panel git-history-panel">
    <h2 class="panel__title">Commit History</h2>

    <!-- Frequency chart -->
    <div v-if="commits.monthly_frequency.length">
      <TimelineFilter
        :data="commits.monthly_frequency"
        :day-data="dayData"
        @update:filtered="filteredMonthly = $event"
        @change="onFilterChange"
      />
      <div class="chart-wrapper" style="margin-top: 1rem">
        <Line v-if="dayChartData ? dayChartData.length : filteredMonthly.length" :data="chartData" :options="chartOptions" />
        <div v-else class="empty-state">No data for selected range</div>
      </div>
    </div>
    <div v-else class="empty-state">No commit data available</div>

    <!-- Stats row -->
    <div class="git-history-stats">
      <span class="git-history-stat">
        <strong>{{ commits.total_commits.toLocaleString() }}</strong> commits
      </span>
      <span class="git-history-stat__sep">·</span>
      <span class="git-history-stat">
        <strong>{{ commits.total_contributors }}</strong> contributors
      </span>
      <span class="git-history-stat__sep">·</span>
      <span class="git-history-stat">
        last <strong>{{ commits.days_since_last_commit ?? '?' }}d</strong> ago
      </span>
      <template v-if="(commits.reverted_commits?.length ?? 0) > 0">
        <span class="git-history-stat__sep">·</span>
        <span class="git-history-stat git-history-stat--warn">
          <strong>{{ commits.reverted_commits!.length }}</strong> reverts
        </span>
      </template>
    </div>

    <!-- Contributors (filtered by date range) -->
    <div v-if="contributors.length" class="git-contribs">
      <div class="git-contribs__label">
        Contributors
        <span v-if="selection.year !== 'All' || selection.months.size > 0 || selection.days.size > 0" class="git-contribs__filter-note">
          (in selected range)
        </span>
      </div>
      <div class="git-contribs__row">
        <a
          v-for="c in contributors"
          :key="c.name"
          :href="c.profileUrl ?? undefined"
          :target="c.profileUrl ? '_blank' : undefined"
          rel="noopener noreferrer"
          :class="['git-contrib', c.profileUrl && 'git-contrib--link']"
          :title="`${c.name} — ${c.commitCount} commits`"
        >
          <img
            v-if="c.avatarUrl"
            :src="c.avatarUrl"
            :alt="c.name"
            class="git-contrib__avatar"
            :style="{ borderColor: c.color }"
          />
          <span
            v-else
            class="git-contrib__initials"
            :style="{ background: c.color + '22', color: c.color, borderColor: c.color }"
          >{{ c.initials }}</span>
          <span class="git-contrib__name">{{ c.name.replace(/\[bot\]/, '').split(' ')[0] }}</span>
          <span class="git-contrib__count">{{ c.commitCount }}</span>
        </a>
      </div>
    </div>

    <!-- Git log graph -->
    <div class="git-log-section">
      <div class="git-log-toolbar">
        <div class="git-log-toolbar__left">
          <span class="git-log-toolbar__title">
            git log --graph
            <span class="git-log-toolbar__count">({{ totalCommits.toLocaleString() }})</span>
          </span>
          <span v-if="commitDateRange" class="git-log-toolbar__range">{{ commitDateRange }}</span>
        </div>
        <input v-model="searchQuery" class="git-log-search" placeholder="Filter commits, authors, shas…" />
      </div>

      <div v-if="graphRows.length" ref="graphScrollEl" class="git-graph-scroll">
        <GitGraphSvg :rows="graphRows" @click-month="activeMonth = $event" @click-body="activeCommitBody = $event" />
      </div>
      <div v-else-if="searchQuery" class="empty-state" style="margin-top:1rem">
        No commits match "{{ searchQuery }}"
      </div>
      <div v-else class="empty-state" style="margin-top:1rem">
        No commit data for selected range
      </div>
    </div>
  </div>

  <CommitMonthDrawer
    :month="activeMonth"
    :commits="activeMonthCommits"
    :repo-url="repoUrl"
    @close="activeMonth = null"
  />

  <CommitBodyDrawer
    :commit="activeCommitBody"
    @close="activeCommitBody = null"
  />
</template>
