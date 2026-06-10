<script setup lang="ts">
import AppTabs from '../ui/AppTabs.vue'
import ArchitectureToursPanel from './ArchitectureToursPanel.vue'
import ContributionPathPanel from './ContributionPathPanel.vue'
import type { ArchTour, ContributionOpportunity } from '../../stores/analysis'

const SECTIONS = ['Guided', 'Start Here'] as const

defineProps<{
  section: string
  tours: ArchTour[]
  opportunities: ContributionOpportunity[]
  repoUrl?: string
  runId?: string
  allFiles?: string[]
}>()

const emit = defineEmits<{ 'update:section': [section: string] }>()
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Architecture Tours</h2>
    <p class="panel__subtitle">Guided reading paths and area-specific contribution entry points.</p>

    <div class="panel__sub-tabs">
      <AppTabs
        :tabs="[...SECTIONS]"
        :model-value="section"
        @update:model-value="emit('update:section', $event)"
      />
    </div>

    <ArchitectureToursPanel
      v-if="section === 'Guided'"
      :tours="tours"
      :repo-url="repoUrl"
      :run-id="runId"
      embedded
    />
    <ContributionPathPanel
      v-else-if="section === 'Start Here'"
      :tours="tours"
      :opportunities="opportunities"
      :repo-url="repoUrl"
      :all-files="allFiles"
      embedded
    />
  </div>
</template>
