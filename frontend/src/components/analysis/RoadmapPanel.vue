<script setup lang="ts">
import { computed } from 'vue'
import RoadmapTimeline from './RoadmapTimeline.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{
  result: RunResult
  repoUrl?: string
}>()

const roadmapFile = computed(() => props.result.structure?.roadmap_file ?? 'ROADMAP.md')
const milestones = computed(() => props.result.structure?.roadmap_parsed?.milestones ?? [])
const roadmapUrl = computed(() => {
  if (!props.repoUrl) return null
  const base = props.repoUrl.replace(/\/$/, '')
  return `${base}/blob/HEAD/${roadmapFile.value}`
})
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Project Roadmap</h2>
    <p class="panel__subtitle">
      Milestones parsed from
      <a v-if="roadmapUrl" :href="roadmapUrl" target="_blank" rel="noopener noreferrer" class="roadmap-panel__file-link">{{ roadmapFile }}</a>
      <code v-else>{{ roadmapFile }}</code>
      — section headers, dates, and checklist items.
    </p>

    <RoadmapTimeline
      v-if="milestones.length"
      :milestones="milestones"
      :roadmap-file="roadmapFile"
    />
    <p v-else class="empty-state">No roadmap file found in this repository.</p>
  </div>
</template>
