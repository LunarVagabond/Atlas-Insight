<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DiffData } from '../../stores/analysis'

const props = defineProps<{
  diffData: DiffData
  loading: boolean
}>()

const expanded = ref(false)

const hasChanges = computed(() => {
  if (!props.diffData.available) return false
  const d = props.diffData
  const hChanged = (d.heuristics ?? []).some(h => h.direction !== 'same')
  const depsChanged = (d.dependencies?.added_count ?? 0) + (d.dependencies?.removed_count ?? 0) > 0
  const structChanged = Math.abs(d.structure?.files_delta ?? 0) > 0
  const gmChanged = (d.graph?.god_modules_delta ?? 0) !== 0
  return hChanged || depsChanged || structChanged || gmChanged
})

const signalChanges = computed(() =>
  (props.diffData.heuristics ?? []).filter(h => h.direction !== 'same')
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 6)
)

const summaryLine = computed(() => {
  if (!props.diffData.available) return null
  const parts: string[] = []
  const fd = props.diffData.structure?.files_delta ?? 0
  if (fd !== 0) parts.push(`${fd > 0 ? '+' : ''}${fd} files`)
  const ac = props.diffData.dependencies?.added_count ?? 0
  const rc = props.diffData.dependencies?.removed_count ?? 0
  if (ac) parts.push(`+${ac} deps`)
  if (rc) parts.push(`-${rc} deps`)
  const cd = props.diffData.contributors?.delta ?? 0
  if (cd !== 0) parts.push(`${cd > 0 ? '+' : ''}${cd} contributors`)
  const gmd = props.diffData.graph?.god_modules_delta ?? 0
  if (gmd !== 0) parts.push(`${gmd > 0 ? '+' : ''}${gmd} god modules`)
  return parts.length ? parts.join(' · ') : 'No structural changes'
})

function deltaClass(direction: string) {
  return direction === 'up' ? 'delta-pill--up' : direction === 'down' ? 'delta-pill--down' : 'delta-pill--same'
}

function deltaSign(delta: number) {
  return delta > 0 ? `+${delta}` : `${delta}`
}

function clsChanged(cls?: { changed: boolean; before_label: string; after_label: string } | null) {
  return cls?.changed
}
</script>

<template>
  <div v-if="loading" class="delta-bar delta-bar--loading">
    <span class="spinner spinner--sm" />
    <span class="delta-bar__loading-text">Comparing with previous analysis…</span>
  </div>

  <div v-else-if="diffData.available" class="delta-bar" :class="hasChanges ? 'delta-bar--has-changes' : 'delta-bar--no-changes'">
    <div class="delta-bar__header" @click="expanded = !expanded">
      <span class="delta-bar__icon">{{ hasChanges ? '↕' : '✓' }}</span>
      <span class="delta-bar__label">Since last analysis</span>
      <span class="delta-bar__summary">{{ summaryLine }}</span>
      <span class="delta-bar__toggle">{{ expanded ? '▲' : '▼' }}</span>
    </div>

    <div v-if="expanded" class="delta-bar__body">
      <!-- Heuristic score changes -->
      <div v-if="signalChanges.length" class="delta-section">
        <div class="delta-section__title">Health Signal Changes</div>
        <div class="delta-signals">
          <div v-for="h in signalChanges" :key="h.signal" class="delta-signal">
            <span class="delta-signal__label">{{ h.label }}</span>
            <span class="delta-signal__scores">
              <span class="delta-signal__before">{{ h.before }}</span>
              <span class="delta-signal__arrow">→</span>
              <span class="delta-signal__after">{{ h.after }}</span>
            </span>
            <span :class="['delta-pill', deltaClass(h.direction)]">{{ deltaSign(h.delta) }}</span>
          </div>
        </div>
      </div>

      <!-- Classification changes -->
      <div v-if="diffData.classification" class="delta-section">
        <template v-for="(cls, key) in diffData.classification" :key="key">
          <div v-if="clsChanged(cls)" class="delta-classification">
            <span class="delta-classification__key">{{ key.replace(/_/g, ' ') }}</span>
            <span class="delta-classification__before">{{ cls!.before_label }}</span>
            <span class="delta-classification__arrow">→</span>
            <span class="delta-classification__after">{{ cls!.after_label }}</span>
          </div>
        </template>
      </div>

      <!-- Dependencies -->
      <div v-if="(diffData.dependencies?.added_count ?? 0) + (diffData.dependencies?.removed_count ?? 0) > 0" class="delta-section">
        <div class="delta-section__title">Dependency Changes</div>
        <div class="delta-deps">
          <div v-if="diffData.dependencies!.added.length" class="delta-deps__group">
            <span class="delta-deps__label delta-deps__label--added">Added</span>
            <div class="delta-deps__list">
              <code v-for="dep in diffData.dependencies!.added.slice(0, 8)" :key="dep" class="delta-dep-chip delta-dep-chip--added">{{ dep }}</code>
              <span v-if="diffData.dependencies!.added_count > 8" class="delta-deps__more">+{{ diffData.dependencies!.added_count - 8 }} more</span>
            </div>
          </div>
          <div v-if="diffData.dependencies!.removed.length" class="delta-deps__group">
            <span class="delta-deps__label delta-deps__label--removed">Removed</span>
            <div class="delta-deps__list">
              <code v-for="dep in diffData.dependencies!.removed.slice(0, 8)" :key="dep" class="delta-dep-chip delta-dep-chip--removed">{{ dep }}</code>
              <span v-if="diffData.dependencies!.removed_count > 8" class="delta-deps__more">+{{ diffData.dependencies!.removed_count - 8 }} more</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Structure side-by-side -->
      <div class="delta-section">
        <div class="delta-section__title">Before / After</div>
        <div class="delta-sbs">
          <div class="delta-sbs__col delta-sbs__col--header">
            <span>Metric</span>
            <span>Previous</span>
            <span>Current</span>
            <span>Change</span>
          </div>
          <div class="delta-sbs__col delta-sbs__col--row">
            <span>Files</span>
            <span class="delta-sbs__val">{{ diffData.structure?.files_before }}</span>
            <span class="delta-sbs__val">{{ diffData.structure?.files_after }}</span>
            <span :class="['delta-pill', 'delta-pill--neutral']" v-if="diffData.structure?.files_delta !== 0">{{ deltaSign(diffData.structure!.files_delta) }}</span>
            <span v-else class="delta-sbs__neutral">—</span>
          </div>
          <div class="delta-sbs__col delta-sbs__col--row">
            <span>Test ratio</span>
            <span class="delta-sbs__val">{{ ((diffData.structure?.test_ratio_before ?? 0) * 100).toFixed(1) }}%</span>
            <span class="delta-sbs__val">{{ ((diffData.structure?.test_ratio_after ?? 0) * 100).toFixed(1) }}%</span>
            <span class="delta-sbs__neutral">—</span>
          </div>
          <div class="delta-sbs__col delta-sbs__col--row">
            <span>Contributors</span>
            <span class="delta-sbs__val">{{ diffData.contributors?.before }}</span>
            <span class="delta-sbs__val">{{ diffData.contributors?.after }}</span>
            <span v-if="diffData.contributors?.delta !== 0" :class="['delta-pill', diffData.contributors!.delta > 0 ? 'delta-pill--up' : 'delta-pill--down']">{{ deltaSign(diffData.contributors!.delta) }}</span>
            <span v-else class="delta-sbs__neutral">—</span>
          </div>
          <div class="delta-sbs__col delta-sbs__col--row">
            <span>Graph nodes</span>
            <span class="delta-sbs__val">{{ diffData.graph?.nodes_before }}</span>
            <span class="delta-sbs__val">{{ diffData.graph?.nodes_after }}</span>
            <span v-if="diffData.graph?.nodes_delta !== 0" :class="['delta-pill', 'delta-pill--neutral']">{{ deltaSign(diffData.graph!.nodes_delta) }}</span>
            <span v-else class="delta-sbs__neutral">—</span>
          </div>
          <div class="delta-sbs__col delta-sbs__col--row">
            <span>God modules</span>
            <span class="delta-sbs__val">{{ diffData.graph?.god_modules_before }}</span>
            <span class="delta-sbs__val">{{ diffData.graph?.god_modules_after }}</span>
            <span v-if="diffData.graph?.god_modules_delta !== 0" :class="['delta-pill', diffData.graph!.god_modules_delta > 0 ? 'delta-pill--down' : 'delta-pill--up']">{{ deltaSign(diffData.graph!.god_modules_delta) }}</span>
            <span v-else class="delta-sbs__neutral">—</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
