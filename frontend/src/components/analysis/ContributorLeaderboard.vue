<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CommitData, GitHubContributor } from '../../stores/analysis'
import type { ContributorStat } from '../../types/commits'
import type { FilterSelection } from './TimelineFilter.vue'
import { commitInDayFilter, isFilterActive, monthInFilter } from '../../composables/timelineFilterUtils'
import { EXTERNAL_IMG_ATTRS } from '../../utils/externalImage'

type LeaderboardMetric = 'commits' | 'lines' | 'net'

const props = defineProps<{
  commits: CommitData
  selection: FilterSelection
  githubContributors?: GitHubContributor[]
  embedded?: boolean
}>()

const metric = ref<LeaderboardMetric>('commits')

const PALETTE = [
  '#0969da', '#7c3aed', '#059669', '#d97706',
  '#dc2626', '#0891b2', '#db2777', '#65a30d',
]

function authorInitials(name: string): string {
  const clean = name.replace(/\[bot\]/, '').trim()
  const parts = clean.split(/[\s._-]+/).filter(Boolean)
  return parts.length >= 2 ? (parts[0][0] + parts[1][0]).toUpperCase() : clean.slice(0, 2).toUpperCase()
}

interface LeaderboardRow {
  author: string
  initials: string
  color: string
  commits: number
  linesAdded: number
  linesRemoved: number
  netLines: number
  avatarUrl?: string
  profileUrl?: string
}

function aggregateFromMonthlyCommits(): LeaderboardRow[] {
  const mc = props.commits.monthly_commits ?? {}
  const counts = new Map<string, number>()
  for (const [month, monthCommits] of Object.entries(mc)) {
    if (isFilterActive(props.selection) && !monthInFilter(month, props.selection)) continue
    for (const c of monthCommits) {
      if (!commitInDayFilter(c.date, props.selection)) continue
      counts.set(c.author, (counts.get(c.author) ?? 0) + 1)
    }
  }
  const ghMap = new Map<string, GitHubContributor>()
  for (const g of props.githubContributors ?? []) ghMap.set(g.login, g)

  return Array.from(counts.entries()).map(([author, commits], idx) => {
    const gh = ghMap.get(author) ?? ghMap.get(author.replace(/\[bot\]/, ''))
    return {
      author,
      initials: authorInitials(author),
      color: PALETTE[idx % PALETTE.length],
      commits,
      linesAdded: 0,
      linesRemoved: 0,
      netLines: 0,
      avatarUrl: gh?.avatar_url,
      profileUrl: gh?.html_url,
    }
  })
}

function aggregateFromContributorStats(stats: ContributorStat[]): LeaderboardRow[] {
  const ghMap = new Map<string, GitHubContributor>()
  for (const g of props.githubContributors ?? []) ghMap.set(g.login, g)
  const filtered = isFilterActive(props.selection)
  const dayFilter = props.selection.days.size > 0

  return stats.map((stat, idx) => {
    let commits = stat.commits
    let linesAdded = stat.lines_added
    let linesRemoved = stat.lines_removed

    if (filtered) {
      commits = 0
      linesAdded = 0
      linesRemoved = 0
      for (const [month, bucket] of Object.entries(stat.monthly ?? {})) {
        if (!monthInFilter(month, props.selection)) continue
        commits += bucket.commits
        if (!dayFilter) {
          linesAdded += bucket.lines_added
          linesRemoved += bucket.lines_removed
        }
      }
      if (dayFilter) {
        const mc = props.commits.monthly_commits ?? {}
        commits = 0
        for (const [month, monthCommits] of Object.entries(mc)) {
          if (!monthInFilter(month, props.selection)) continue
          for (const c of monthCommits) {
            if (c.author !== stat.author && c.author.toLowerCase() !== stat.author.toLowerCase()) continue
            if (!commitInDayFilter(c.date, props.selection)) continue
            commits += 1
          }
        }
      }
    }

    const gh = ghMap.get(stat.author) ?? ghMap.get(stat.author.replace(/\[bot\]/, ''))
    return {
      author: stat.author,
      initials: authorInitials(stat.author),
      color: PALETTE[idx % PALETTE.length],
      commits,
      linesAdded,
      linesRemoved,
      netLines: linesAdded - linesRemoved,
      avatarUrl: gh?.avatar_url,
      profileUrl: gh?.html_url,
    }
  }).filter(r => r.commits > 0 || r.linesAdded > 0 || r.linesRemoved > 0)
}

const rows = computed<LeaderboardRow[]>(() => {
  const stats = props.commits.contributor_stats
  const base = stats?.length ? aggregateFromContributorStats(stats) : aggregateFromMonthlyCommits()
  const sortKey = metric.value === 'commits'
    ? (r: LeaderboardRow) => r.commits
    : metric.value === 'lines'
      ? (r: LeaderboardRow) => r.linesAdded + r.linesRemoved
      : (r: LeaderboardRow) => Math.abs(r.netLines)
  return [...base].sort((a, b) => sortKey(b) - sortKey(a))
})

const showLineStats = computed(() =>
  (props.commits.contributor_stats?.length ?? 0) > 0 && props.selection.days.size === 0,
)

const lineStatsDisabledReason = computed(() => {
  if (props.selection.days.size > 0) {
    return 'Line stats are available for month/year filters only, not day-level filters.'
  }
  if (!props.commits.contributor_stats?.length) {
    return 'Re-run analysis on this repository to load line add/delete stats.'
  }
  return ''
})

const hasData = computed(() => rows.value.length > 0)

const needsReanalysis = computed(() =>
  !props.commits.contributor_stats?.length && hasData.value,
)

function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 10_000) return `${(n / 1_000).toFixed(1)}k`
  return n.toLocaleString()
}
</script>

<template>
  <div :class="['contributor-leaderboard', !embedded && 'panel', embedded && 'contributor-leaderboard--embedded']">
    <div class="contributor-leaderboard__header">
      <div>
        <h3 class="contributor-leaderboard__title">Contributor Leaderboard</h3>
        <p class="contributor-leaderboard__subtitle">
          All contributors in the last 2 years
          <span v-if="isFilterActive(selection)" class="contributor-leaderboard__filter-note">(filtered)</span>
        </p>
        <p v-if="needsReanalysis" class="contributor-leaderboard__hint contributor-leaderboard__hint--cta">
          Line add/delete stats require a fresh analysis. Re-submit the repository URL to refresh this run.
        </p>
      </div>
      <div v-if="hasData" class="contributor-leaderboard__metrics" role="group" aria-label="Sort metric">
        <button
          type="button"
          :class="['contributor-leaderboard__metric', metric === 'commits' && 'contributor-leaderboard__metric--active']"
          @click="metric = 'commits'"
        >Commits</button>
        <button
          type="button"
          :class="['contributor-leaderboard__metric', metric === 'lines' && 'contributor-leaderboard__metric--active']"
          :disabled="!showLineStats"
          :title="!showLineStats ? lineStatsDisabledReason : undefined"
          @click="metric = 'lines'"
        >Lines changed</button>
        <button
          type="button"
          :class="['contributor-leaderboard__metric', metric === 'net' && 'contributor-leaderboard__metric--active']"
          :disabled="!showLineStats"
          :title="!showLineStats ? lineStatsDisabledReason : undefined"
          @click="metric = 'net'"
        >Net lines</button>
      </div>
    </div>

    <div v-if="hasData" class="contributor-leaderboard__scroll">
      <table class="contributor-leaderboard__table">
        <thead>
          <tr>
            <th class="contributor-leaderboard__col-rank">#</th>
            <th class="contributor-leaderboard__col-author">Contributor</th>
            <th class="contributor-leaderboard__col-num">Commits</th>
            <th v-if="showLineStats" class="contributor-leaderboard__col-num">+Lines</th>
            <th v-if="showLineStats" class="contributor-leaderboard__col-num">−Lines</th>
            <th v-if="showLineStats" class="contributor-leaderboard__col-num">Net</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="row.author">
            <td class="contributor-leaderboard__col-rank">{{ idx + 1 }}</td>
            <td class="contributor-leaderboard__col-author">
              <a
                :href="row.profileUrl ?? undefined"
                :target="row.profileUrl ? '_blank' : undefined"
                rel="noopener noreferrer"
                :class="['contributor-leaderboard__identity', row.profileUrl && 'contributor-leaderboard__identity--link']"
              >
                <img
                  v-if="row.avatarUrl"
                  :src="row.avatarUrl"
                  :alt="row.author"
                  class="contributor-leaderboard__avatar"
                  :style="{ borderColor: row.color }"
                  v-bind="EXTERNAL_IMG_ATTRS"
                />
                <span
                  v-else
                  class="contributor-leaderboard__initials"
                  :style="{ background: row.color + '22', color: row.color, borderColor: row.color }"
                >{{ row.initials }}</span>
                <span class="contributor-leaderboard__name">{{ row.author.replace(/\[bot\]/, '') }}</span>
              </a>
            </td>
            <td class="contributor-leaderboard__col-num">{{ formatNum(row.commits) }}</td>
            <td v-if="showLineStats" class="contributor-leaderboard__col-num contributor-leaderboard__col-add">
              +{{ formatNum(row.linesAdded) }}
            </td>
            <td v-if="showLineStats" class="contributor-leaderboard__col-num contributor-leaderboard__col-del">
              −{{ formatNum(row.linesRemoved) }}
            </td>
            <td v-if="showLineStats" class="contributor-leaderboard__col-num" :class="row.netLines >= 0 ? 'contributor-leaderboard__col-add' : 'contributor-leaderboard__col-del'">
              {{ row.netLines >= 0 ? '+' : '' }}{{ formatNum(row.netLines) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="empty-state contributor-leaderboard__empty">
      No contributors in the selected time range.
    </div>
  </div>
</template>
