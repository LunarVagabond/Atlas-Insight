<script setup lang="ts">
import AppBadge from '../ui/AppBadge.vue'

defineProps<{
  staleBranches: { name: string; last_commit: string; days_ago: number }[]
  staleBranchCount: number
}>()

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function severityVariant(daysAgo: number): 'warning' | 'failed' | 'info' {
  if (daysAgo > 365) return 'failed'
  if (daysAgo > 180) return 'warning'
  return 'info'
}
</script>

<template>
  <div v-if="staleBranchCount > 0" class="stale-branches">
    <div class="stale-branches__header">
      <h3 class="stale-branches__title">Stale Branches</h3>
      <AppBadge :variant="staleBranchCount > 5 ? 'failed' : 'warning'">
        {{ staleBranchCount }} stale {{ staleBranchCount === 1 ? 'branch' : 'branches' }}
      </AppBadge>
    </div>
    <p class="stale-branches__subtitle">Remote branches with no commits in 90+ days.</p>

    <div class="stale-branches__table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Branch</th>
            <th>Last Commit</th>
            <th>Inactive</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="branch in staleBranches" :key="branch.name">
            <td><code class="stale-branches__branch-name">{{ branch.name }}</code></td>
            <td>{{ formatDate(branch.last_commit) }}</td>
            <td>
              <AppBadge :variant="severityVariant(branch.days_ago)">
                {{ branch.days_ago }}d ago
              </AppBadge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-else class="stale-branches stale-branches--clean">
    <span class="stale-branches__clean-icon">✓</span>
    <span>No stale branches detected (all active within 90 days).</span>
  </div>
</template>
