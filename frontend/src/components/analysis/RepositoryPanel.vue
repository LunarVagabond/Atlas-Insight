<script setup lang="ts">
import { computed } from 'vue'
import AppTabs from '../ui/AppTabs.vue'
import ProjectPanel from './ProjectPanel.vue'
import CommitTimelineChart from './CommitTimelineChart.vue'
import RoadmapTimeline from './RoadmapTimeline.vue'
import StaleBranchesPanel from './StaleBranchesPanel.vue'
import type { RunResult } from '../../stores/analysis'
import type { CommitData } from '../../types/commits'
import type { GitHubContributor } from '../../stores/analysis'

const SECTIONS = ['Profile', 'Activity', 'Branches'] as const

const props = defineProps<{
  result: RunResult
  section: string
  repoUrl?: string
  commits?: CommitData
  githubContributors?: GitHubContributor[]
}>()

const emit = defineEmits<{ 'update:section': [section: string] }>()

const hasRoadmap = computed(
  () => (props.result.structure?.roadmap_parsed?.milestones?.length ?? 0) > 0,
)
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Repository</h2>
    <p class="panel__subtitle">Project metadata, commit activity, and branch hygiene.</p>

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
      <div v-if="hasRoadmap && result.structure?.roadmap_parsed" class="panel panel--nested">
        <RoadmapTimeline
          :milestones="result.structure.roadmap_parsed.milestones"
          :roadmap-file="result.structure.roadmap_file ?? 'ROADMAP.md'"
        />
      </div>
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
