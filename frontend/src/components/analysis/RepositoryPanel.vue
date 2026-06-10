<script setup lang="ts">
import AppTabs from '../ui/AppTabs.vue'
import ProjectPanel from './ProjectPanel.vue'
import CommitTimelineChart from './CommitTimelineChart.vue'
import StaleBranchesPanel from './StaleBranchesPanel.vue'
import type { RunResult } from '../../stores/analysis'
import type { CommitData } from '../../types/commits'
import type { GitHubContributor } from '../../stores/analysis'

const SECTIONS = ['Profile', 'Activity', 'Branches'] as const

defineProps<{
  result: RunResult
  section: string
  repoUrl?: string
  commits?: CommitData
  githubContributors?: GitHubContributor[]
}>()

const emit = defineEmits<{ 'update:section': [section: string] }>()
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Repository</h2>
    <p class="panel__subtitle">Project metadata, commit activity, and branch hygiene. See the Roadmap tab when a roadmap file is present.</p>

    <div class="panel__sub-tabs">
      <AppTabs
        :tabs="[...SECTIONS]"
        :model-value="section"
        @update:model-value="emit('update:section', $event)"
      />
    </div>

    <template v-if="section === 'Profile'">
      <ProjectPanel :result="result" embedded />
    </template>

    <template v-else-if="section === 'Activity'">
      <CommitTimelineChart
        v-if="commits"
        :commits="commits"
        :repo-url="repoUrl"
        :github-contributors="githubContributors"
        embedded
      />
      <p v-else class="empty-state">No commit data available.</p>
    </template>

    <template v-else-if="section === 'Branches'">
      <StaleBranchesPanel
        v-if="result.structure"
        :stale-branches="result.structure.stale_branches ?? []"
        :stale-branch-count="result.structure.stale_branch_count ?? 0"
      />
      <p v-else class="empty-state">No branch data available.</p>
    </template>
  </div>
</template>
