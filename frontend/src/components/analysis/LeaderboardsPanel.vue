<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CommitData, GitHubContributor } from '../../stores/analysis'
import TimelineFilter, { type FilterSelection } from './TimelineFilter.vue'
import ContributorLeaderboard from './ContributorLeaderboard.vue'
import ContributorGraph from './ContributorGraph.vue'

const props = defineProps<{
  commits: CommitData
  githubContributors?: GitHubContributor[]
}>()

const selection = ref<FilterSelection>({ year: 'All', months: new Set(), days: new Set() })

const dayData = computed<Record<string, number[]>>(() => {
  const mc = props.commits.monthly_commits ?? {}
  const result: Record<string, number[]> = {}
  for (const [month, commits] of Object.entries(mc)) {
    const days = new Set(commits.map(c => parseInt(c.date.slice(8, 10))))
    result[month] = Array.from(days).sort((a, b) => a - b)
  }
  return result
})

const hasRecentActivity = computed(() => (props.commits.monthly_frequency?.length ?? 0) > 0)
</script>

<template>
  <div class="panel leaderboards-panel">
    <h2 class="panel__title">Leaderboards</h2>

    <div v-if="hasRecentActivity">
      <TimelineFilter
        :data="commits.monthly_frequency"
        :day-data="dayData"
        @change="selection = $event"
      />
    </div>
    <div v-else-if="commits.total_commits > 0" class="stale-branch-notice">
      <span class="stale-branch-notice__icon">🕰</span>
      <div class="stale-branch-notice__body">
        <strong>Stale branch</strong> — no commits in the last 2 years.
        <span v-if="commits.last_commit_date">
          Last activity {{ new Date(commits.last_commit_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short' }) }}.
        </span>
      </div>
    </div>
    <div v-else class="empty-state">No commit data available</div>

    <ContributorLeaderboard
      v-if="commits.total_commits > 0"
      :commits="commits"
      :selection="selection"
      :github-contributors="githubContributors"
      embedded
    />

    <ContributorGraph
      v-if="hasRecentActivity"
      :commits="commits"
      :selection="selection"
    />
  </div>
</template>
