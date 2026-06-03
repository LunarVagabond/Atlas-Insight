<script setup lang="ts">
import { ref, computed } from 'vue'
import AppBadge from '../ui/AppBadge.vue'

const props = defineProps<{
  staleBranches: { name: string; last_commit: string; days_ago: number }[]
  staleBranchCount: number
}>()

const PAGE_SIZE = 10
const page = ref(1)

const totalPages = computed(() => Math.ceil(props.staleBranches.length / PAGE_SIZE))

const pagedBranches = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return props.staleBranches.slice(start, start + PAGE_SIZE)
})

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
      <div class="stale-branches__header-left">
        <h3 class="stale-branches__title">Stale Branches</h3>
        <p class="stale-branches__subtitle">Remote branches with no commits in 90+ days.</p>
      </div>
      <AppBadge :variant="staleBranchCount > 5 ? 'failed' : 'warning'" class="stale-branches__count-badge">
        {{ staleBranchCount }} {{ staleBranchCount === 1 ? 'branch' : 'branches' }}
      </AppBadge>
    </div>

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
          <tr v-for="branch in pagedBranches" :key="branch.name">
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

    <div v-if="totalPages > 1" class="stale-branches__pagination">
      <button
        class="stale-branches__page-btn"
        :disabled="page === 1"
        @click="page--"
      >&#8592;</button>
      <span class="stale-branches__page-info">{{ page }} / {{ totalPages }}</span>
      <button
        class="stale-branches__page-btn"
        :disabled="page === totalPages"
        @click="page++"
      >&#8594;</button>
    </div>
  </div>
  <div v-else class="stale-branches stale-branches--clean">
    <span class="stale-branches__clean-icon">✓</span>
    <span>No stale branches detected (all active within 90 days).</span>
  </div>
</template>
