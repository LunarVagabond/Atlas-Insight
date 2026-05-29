<script setup lang="ts">
import AppBadge from '../ui/AppBadge.vue'
import AppCard from '../ui/AppCard.vue'
import type { DepsData } from '../../stores/analysis'

defineProps<{ deps: DepsData }>()
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Dependencies</h2>

    <div class="panel__grid" style="grid-template-columns: repeat(2, 1fr); margin-bottom: 1.5rem">
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ deps.dependency_count }}</div>
          <div class="stat__label">Total Dependencies</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ deps.docker_issues.length }}</div>
          <div class="stat__label">Docker Issues</div>
        </div>
      </AppCard>
    </div>

    <div v-if="deps.missing_lockfile_warnings.length" style="margin-bottom: 1.5rem">
      <div v-for="(w, i) in deps.missing_lockfile_warnings" :key="i" class="warning-row">
        <AppBadge variant="warning">Warning</AppBadge>
        <span>{{ w }}</span>
      </div>
    </div>

    <div v-if="deps.docker_issues.length" style="margin-bottom: 1.5rem">
      <h3 class="panel__title">Docker Issues</h3>
      <table class="data-table">
        <thead>
          <tr><th>File</th><th>Issue</th></tr>
        </thead>
        <tbody>
          <tr v-for="(issue, i) in deps.docker_issues" :key="i">
            <td>{{ issue.file }}</td>
            <td><AppBadge variant="warning">{{ issue.issue }}</AppBadge></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="deps.dependencies.length">
      <h3 class="panel__title">All Dependencies</h3>
      <table class="data-table">
        <thead>
          <tr><th>Package</th><th>Version</th><th>Source</th><th>Type</th></tr>
        </thead>
        <tbody>
          <tr v-for="(dep, i) in deps.dependencies" :key="i">
            <td>{{ dep.name }}</td>
            <td>{{ dep.version_spec || '—' }}</td>
            <td>{{ dep.source }}</td>
            <td>
              <AppBadge v-if="dep.dev" variant="info">dev</AppBadge>
              <AppBadge v-else variant="completed">prod</AppBadge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!deps.dependencies.length && !deps.docker_issues.length" class="empty-state">
      No dependency files found
    </div>
  </div>
</template>
