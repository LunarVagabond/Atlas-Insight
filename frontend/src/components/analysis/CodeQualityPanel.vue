<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import AppTabs from '../ui/AppTabs.vue'
import type { ComplexityData, DeadCodeData, JunkFilesData, TestCoverageData } from '../../stores/analysis'

const SECTIONS = ['Tests', 'Complexity', 'Dead Code', 'Clutter'] as const

const CATEGORY_LABELS: Record<string, string> = {
  os_junk: 'OS junk',
  editor_swap: 'Editor swap',
  temp_file: 'Temp file',
  log_file: 'Log file',
  build_artifact: 'Build artifact',
  gitignore_gap: 'Gitignore gap',
  ai_scratch: 'AI/scratch',
}

const props = defineProps<{
  complexity?: ComplexityData
  deadCode?: DeadCodeData
  junkFiles?: JunkFilesData
  testCoverage?: TestCoverageData
  section?: string
}>()

const emit = defineEmits<{ 'update:section': [section: string] }>()

const activeSection = computed(() =>
  props.section && SECTIONS.includes(props.section as typeof SECTIONS[number])
    ? props.section
    : 'Tests',
)

function riskLevel(score: number): 'low' | 'medium' | 'high' {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category.replace(/_/g, ' ')
}

const testRatioPercent = computed(() =>
  props.testCoverage ? Math.round((props.testCoverage.test_ratio ?? 0) * 100) : 0
)

const highConfidenceCount = computed(() =>
  (props.junkFiles?.files ?? []).filter(f => f.confidence === 'high').length
)

const distributionTotal = computed(() => {
  const d = props.complexity?.distribution
  if (!d) return 1
  return (d['0-100'] + d['100-300'] + d['300-500'] + d['500+']) || 1
})

function distPct(key: keyof NonNullable<ComplexityData['distribution']>): number {
  const d = props.complexity?.distribution
  if (!d) return 0
  return Math.round((d[key] / distributionTotal.value) * 100)
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Code Quality</h2>
    <p class="panel__subtitle">Static proxy metrics for code health: file size distribution, unreferenced files, clutter detection, and test coverage mapping. No runtime execution — all derived from source files.</p>

    <div class="panel__sub-tabs">
      <AppTabs
        :tabs="[...SECTIONS]"
        :model-value="activeSection"
        @update:model-value="emit('update:section', $event)"
      />
    </div>

    <!-- ── Test coverage ──────────────────────────────────────── -->
    <section v-if="activeSection === 'Tests'" class="cq-section">
      <h3 class="cq-section__title">Test Coverage</h3>
      <div class="panel__grid panel__grid--2col" style="margin-bottom: 1rem">
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ testRatioPercent }}%</div>
            <div class="stat__label">Test File Ratio</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ testCoverage?.test_file_count ?? '—' }}</div>
            <div class="stat__label">Test Files</div>
          </div>
        </AppCard>
      </div>

      <div v-if="testCoverage?.framework_detected" class="cq-framework">
        Framework detected: <AppBadge variant="info">{{ testCoverage.framework_detected }}</AppBadge>
      </div>

      <div v-if="(testCoverage?.untested_dirs?.length ?? 0) > 0" style="margin-top: 1rem">
        <p class="cq-section__subtitle">Directories with source files but no tests:</p>
        <table class="data-table">
          <thead>
            <tr><th>Directory</th><th>Source Files</th></tr>
          </thead>
          <tbody>
            <tr v-for="dir in testCoverage?.untested_dirs?.slice(0, 15)" :key="dir.path">
              <td class="mono">{{ dir.path || '(root)' }}</td>
              <td>{{ dir.source_files }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="testCoverage" class="panel__hint" style="margin-top: 0.75rem">
        No untested directories detected with more than 3 source files.
      </div>
    </section>

    <!-- ── Complexity hotspots ────────────────────────────────── -->
    <section v-else-if="activeSection === 'Complexity'" class="cq-section">
      <h3 class="cq-section__title">Complexity Hotspots</h3>
      <div class="panel__grid panel__grid--2col" style="margin-bottom: 1rem">
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ complexity?.files_over_threshold ?? 0 }}</div>
            <div class="stat__label">Files > {{ complexity?.threshold ?? 500 }} LOC</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ complexity?.avg_file_loc ?? '—' }}</div>
            <div class="stat__label">Avg LOC / File</div>
          </div>
        </AppCard>
      </div>

      <div v-if="complexity?.distribution" class="cq-dist">
        <div class="cq-dist__label">File size distribution</div>
        <div class="cq-dist__bar">
          <div class="cq-dist__seg cq-dist__seg--ok" :style="{ width: distPct('0-100') + '%' }" :title="`0–100 LOC: ${complexity.distribution['0-100']} files`"></div>
          <div class="cq-dist__seg cq-dist__seg--mild" :style="{ width: distPct('100-300') + '%' }" :title="`100–300 LOC: ${complexity.distribution['100-300']} files`"></div>
          <div class="cq-dist__seg cq-dist__seg--warn" :style="{ width: distPct('300-500') + '%' }" :title="`300–500 LOC: ${complexity.distribution['300-500']} files`"></div>
          <div class="cq-dist__seg cq-dist__seg--bad" :style="{ width: distPct('500+') + '%' }" :title="`500+ LOC: ${complexity.distribution['500+']} files`"></div>
        </div>
        <div class="cq-dist__legend">
          <span class="cq-dist__legend-item cq-dist__legend-item--ok">0–100</span>
          <span class="cq-dist__legend-item cq-dist__legend-item--mild">100–300</span>
          <span class="cq-dist__legend-item cq-dist__legend-item--warn">300–500</span>
          <span class="cq-dist__legend-item cq-dist__legend-item--bad">500+</span>
        </div>
      </div>

      <div v-if="(complexity?.hotspots?.length ?? 0) > 0" style="margin-top: 1rem">
        <table class="data-table">
          <thead>
            <tr><th>File</th><th>LOC</th><th>Has Test</th></tr>
          </thead>
          <tbody>
            <tr v-for="h in complexity?.hotspots?.slice(0, 20)" :key="h.file">
              <td class="mono cq-truncate">{{ h.file }}</td>
              <td>{{ h.loc.toLocaleString() }}</td>
              <td>
                <AppBadge :variant="h.has_adjacent_test ? 'info' : 'warning'">
                  {{ h.has_adjacent_test ? 'Yes' : 'No' }}
                </AppBadge>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="complexity" class="panel__hint" style="margin-top: 0.75rem">
        No files exceed the {{ complexity.threshold }}-line threshold.
      </div>
    </section>

    <!-- ── Dead code candidates ───────────────────────────────── -->
    <section v-else-if="activeSection === 'Dead Code'" class="cq-section">
      <h3 class="cq-section__title">Unreferenced Files</h3>
      <p class="panel__subtitle" style="margin-top: 0">Files with no inbound imports in the analyzed graph. Entry points and test files are excluded. Requires a reasonably dense import graph — treat as hints, not definitive dead code.</p>

      <div v-if="deadCode?.note" class="panel__hint">{{ deadCode.note }}</div>

      <template v-else-if="(deadCode?.count ?? 0) > 0">
        <div class="panel__grid" style="margin-bottom: 1rem">
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value" :class="`stat__value--${riskLevel(Math.min(100, (deadCode?.count ?? 0) * 2))}`">
                {{ deadCode?.count }}
              </div>
              <div class="stat__label">Unreferenced Files</div>
            </div>
          </AppCard>
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value">{{ deadCode?.filtered_entry_points }}</div>
              <div class="stat__label">Entry Points Excluded</div>
            </div>
          </AppCard>
        </div>

        <table class="data-table">
          <thead>
            <tr><th>File</th><th>Language</th></tr>
          </thead>
          <tbody>
            <tr v-for="entry in deadCode?.unreferenced?.slice(0, 30)" :key="entry.file">
              <td class="mono cq-truncate">{{ entry.file }}</td>
              <td>{{ entry.lang }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="(deadCode?.count ?? 0) > 30" class="panel__hint" style="margin-top: 0.75rem">
          Showing 30 of {{ deadCode?.count }} unreferenced files.
        </p>
      </template>

      <div v-else-if="deadCode && !deadCode.note" class="panel__hint">
        No unreferenced files detected in the import graph.
      </div>
      <div v-else class="panel__hint">Import graph analysis not available.</div>
    </section>

    <!-- ── Repo clutter ───────────────────────────────────────── -->
    <section v-else-if="activeSection === 'Clutter'" class="cq-section">
      <h3 class="cq-section__title">Repo Clutter</h3>
      <p class="panel__subtitle" style="margin-top: 0">Tracked files that match temp, OS junk, backup, log, or common gitignore patterns. Pattern-based hints — review before deleting; some files may be intentional.</p>

      <div v-if="junkFiles?.note" class="panel__hint">{{ junkFiles.note }}</div>

      <template v-if="(junkFiles?.count ?? 0) > 0">
        <div class="panel__grid panel__grid--3col" style="margin-bottom: 1rem">
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value" :class="`stat__value--${riskLevel(junkFiles?.score ?? 0)}`">
                {{ junkFiles?.count }}
              </div>
              <div class="stat__label">Clutter Files</div>
            </div>
          </AppCard>
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value">{{ highConfidenceCount }}</div>
              <div class="stat__label">High Confidence</div>
            </div>
          </AppCard>
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value">{{ formatBytes(junkFiles?.total_bytes ?? 0) }}</div>
              <div class="stat__label">Total Size</div>
            </div>
          </AppCard>
        </div>

        <table class="data-table">
          <thead>
            <tr><th>File</th><th>Category</th><th>Reason</th><th>Confidence</th><th>Size</th></tr>
          </thead>
          <tbody>
            <tr v-for="entry in junkFiles?.files?.slice(0, 50)" :key="entry.path">
              <td class="mono cq-truncate">{{ entry.path }}</td>
              <td><span class="cq-category-chip">{{ categoryLabel(entry.category) }}</span></td>
              <td>{{ entry.reason }}</td>
              <td>
                <span class="cq-confidence" :class="`cq-confidence--${entry.confidence}`">
                  {{ entry.confidence }}
                </span>
              </td>
              <td>{{ entry.size_bytes != null ? formatBytes(entry.size_bytes) : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="(junkFiles?.count ?? 0) > 50" class="panel__hint" style="margin-top: 0.75rem">
          Showing 50 of {{ junkFiles?.count }} clutter files.
        </p>
      </template>

      <div v-else-if="junkFiles" class="panel__hint">
        No clutter files detected in tracked paths.
      </div>
      <div v-else class="panel__hint">Clutter analysis not available.</div>
    </section>
  </div>
</template>
