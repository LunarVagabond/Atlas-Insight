<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { ComplexityData, DeadCodeData, TestCoverageData } from '../../stores/analysis'

const props = defineProps<{
  complexity?: ComplexityData
  deadCode?: DeadCodeData
  testCoverage?: TestCoverageData
}>()

function riskLevel(score: number): 'low' | 'medium' | 'high' {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

const testRatioPercent = computed(() =>
  props.testCoverage ? Math.round((props.testCoverage.test_ratio ?? 0) * 100) : 0
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
    <p class="panel__subtitle">Static proxy metrics for code health: file size distribution, unreferenced files, and test coverage mapping. No runtime execution — all derived from source files.</p>

    <!-- ── Test coverage ──────────────────────────────────────── -->
    <section class="cq-section">
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
    <section class="cq-section">
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

      <!-- Distribution bar -->
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
    <section class="cq-section">
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
  </div>
</template>
