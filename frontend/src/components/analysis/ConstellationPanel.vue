<script setup lang="ts">
import { onMounted } from 'vue'
import { useAnalysisStore } from '../../stores/analysis'
import type { ConstellationRelated } from '../../stores/analysis'

const props = defineProps<{ runId: string }>()

const store = useAnalysisStore()

onMounted(() => {
  if (!store.constellationData && !store.constellationLoading) {
    store.fetchConstellation(props.runId)
  }
})

const REF_LABELS: Record<ConstellationRelated['ref_type'], string> = {
  readme_link: 'README link',
  dep_match: 'dependency',
  same_org_pattern: 'same org',
}

const REF_ICONS: Record<ConstellationRelated['ref_type'], string> = {
  readme_link: '🔗',
  dep_match: '📦',
  same_org_pattern: '🏢',
}
</script>

<template>
  <div v-if="store.constellationLoading" class="constellation__loading">
    Scanning for related repos…
  </div>

  <div
    v-else-if="store.constellationData && store.constellationData.related.length"
    class="constellation"
  >
    <h3 class="constellation__title">Related Repositories</h3>
    <ul class="constellation__list">
      <li
        v-for="rel in store.constellationData.related"
        :key="rel.repo_id"
        class="constellation__item"
      >
        <span class="constellation__ref-icon" :title="REF_LABELS[rel.ref_type]">
          {{ REF_ICONS[rel.ref_type] }}
        </span>
        <span class="constellation__repo">
          <a
            v-if="rel.run_id"
            :href="`/results/${rel.run_id}`"
            class="constellation__repo-link"
          >{{ rel.owner }}/{{ rel.name }}</a>
          <span v-else>{{ rel.owner }}/{{ rel.name }}</span>
        </span>
        <span class="constellation__badge" :class="`constellation__badge--${rel.ref_type}`">
          {{ REF_LABELS[rel.ref_type] }}
        </span>
        <span class="constellation__evidence">{{ rel.evidence }}</span>
      </li>
    </ul>
  </div>
</template>
