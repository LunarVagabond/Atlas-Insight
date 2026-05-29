<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { AnalysisRun } from '../../stores/analysis'

const props = defineProps<{ runA: AnalysisRun; runB: AnalysisRun }>()

type Winner = 'a' | 'b' | 'equal'

function higherBetter(va: number, vb: number): Winner {
  if (va > vb) return 'a'
  if (vb > va) return 'b'
  return 'equal'
}

function lowerBetter(va: number, vb: number): Winner {
  if (va < vb) return 'a'
  if (vb < va) return 'b'
  return 'equal'
}

function cellClass(winner: Winner, side: 'a' | 'b'): string {
  if (winner === 'equal') return 'compare-panel__cell'
  return winner === side ? 'compare-panel__cell compare-panel__cell--better' : 'compare-panel__cell compare-panel__cell--worse'
}

function fmt(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

const clsA = computed(() => props.runA.result?.classification)
const clsB = computed(() => props.runB.result?.classification)
const commitsA = computed(() => props.runA.result?.commits)
const commitsB = computed(() => props.runB.result?.commits)
const structA = computed(() => props.runA.result?.structure)
const structB = computed(() => props.runB.result?.structure)
const graphA = computed(() => props.runA.result?.graph)
const graphB = computed(() => props.runB.result?.graph)
const depsA = computed(() => props.runA.result?.dependencies)
const depsB = computed(() => props.runB.result?.dependencies)
const ghA = computed(() => props.runA.result?.github_meta)
const ghB = computed(() => props.runB.result?.github_meta)

function difficultyVariant(key?: string): string {
  const map: Record<string, string> = { very_easy: 'completed', easy: 'completed', moderate: 'warning', hard: 'warning', very_hard: 'failed' }
  return map[key ?? ''] ?? 'info'
}
function healthVariant(key?: string): string {
  const map: Record<string, string> = { thriving: 'completed', active: 'completed', stable: 'info', declining: 'warning', abandoned: 'failed' }
  return map[key ?? ''] ?? 'info'
}
function complexityVariant(key?: string): string {
  const map: Record<string, string> = { simple: 'completed', moderate: 'info', complex: 'warning', very_complex: 'failed' }
  return map[key ?? ''] ?? 'info'
}
function docVariant(key?: string): string {
  const map: Record<string, string> = { excellent: 'completed', good: 'completed', fair: 'warning', poor: 'warning', missing: 'failed' }
  return map[key ?? ''] ?? 'info'
}
</script>

<template>
  <div class="compare-panel">

    <!-- Repo headers -->
    <div class="compare-panel__header">
      <AppCard>
        <div class="compare-panel__repo-label">
          <a :href="runA.repo_url" target="_blank" rel="noopener noreferrer" class="compare-panel__repo-link">
            {{ runA.repo_owner }}/{{ runA.repo_name }} ↗
          </a>
        </div>
      </AppCard>
      <AppCard>
        <div class="compare-panel__repo-label">
          <a :href="runB.repo_url" target="_blank" rel="noopener noreferrer" class="compare-panel__repo-link">
            {{ runB.repo_owner }}/{{ runB.repo_name }} ↗
          </a>
        </div>
      </AppCard>
    </div>

    <!-- Classification -->
    <section v-if="clsA && clsB" class="compare-panel__section">
      <h2 class="panel__title">Classification</h2>
      <AppCard>
        <div class="compare-panel__metric-label">Contribution Difficulty</div>
        <div class="compare-panel__row">
          <div class="compare-panel__cell">
            <AppBadge :variant="(difficultyVariant(clsA.contribution_difficulty?.key) as any)">
              {{ clsA.contribution_difficulty?.label ?? '—' }}
            </AppBadge>
          </div>
          <div class="compare-panel__cell">
            <AppBadge :variant="(difficultyVariant(clsB.contribution_difficulty?.key) as any)">
              {{ clsB.contribution_difficulty?.label ?? '—' }}
            </AppBadge>
          </div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Project Health</div>
        <div class="compare-panel__row">
          <div class="compare-panel__cell">
            <AppBadge :variant="(healthVariant(clsA.project_health?.key) as any)">
              {{ clsA.project_health?.label ?? '—' }}
            </AppBadge>
          </div>
          <div class="compare-panel__cell">
            <AppBadge :variant="(healthVariant(clsB.project_health?.key) as any)">
              {{ clsB.project_health?.label ?? '—' }}
            </AppBadge>
          </div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Code Complexity</div>
        <div class="compare-panel__row">
          <div class="compare-panel__cell">
            <AppBadge :variant="(complexityVariant(clsA.code_complexity?.key) as any)">
              {{ clsA.code_complexity?.label ?? '—' }}
            </AppBadge>
          </div>
          <div class="compare-panel__cell">
            <AppBadge :variant="(complexityVariant(clsB.code_complexity?.key) as any)">
              {{ clsB.code_complexity?.label ?? '—' }}
            </AppBadge>
          </div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Documentation</div>
        <div class="compare-panel__row">
          <div class="compare-panel__cell">
            <AppBadge :variant="(docVariant(clsA.documentation_grade?.key) as any)">
              {{ clsA.documentation_grade?.label ?? '—' }}
            </AppBadge>
          </div>
          <div class="compare-panel__cell">
            <AppBadge :variant="(docVariant(clsB.documentation_grade?.key) as any)">
              {{ clsB.documentation_grade?.label ?? '—' }}
            </AppBadge>
          </div>
        </div>
      </AppCard>
    </section>

    <!-- Activity stats -->
    <section v-if="commitsA && commitsB" class="compare-panel__section">
      <h2 class="panel__title">Activity</h2>
      <AppCard>
        <div class="compare-panel__metric-label">Total Commits</div>
        <div class="compare-panel__row">
          <div :class="cellClass(higherBetter(commitsA.total_commits, commitsB.total_commits), 'a')">
            {{ fmt(commitsA.total_commits) }}
          </div>
          <div :class="cellClass(higherBetter(commitsA.total_commits, commitsB.total_commits), 'b')">
            {{ fmt(commitsB.total_commits) }}
          </div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Contributors</div>
        <div class="compare-panel__row">
          <div :class="cellClass(higherBetter(commitsA.total_contributors, commitsB.total_contributors), 'a')">
            {{ fmt(commitsA.total_contributors) }}
          </div>
          <div :class="cellClass(higherBetter(commitsA.total_contributors, commitsB.total_contributors), 'b')">
            {{ fmt(commitsB.total_contributors) }}
          </div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Days Since Last Commit</div>
        <div class="compare-panel__row">
          <div :class="cellClass(lowerBetter(commitsA.days_since_last_commit ?? 0, commitsB.days_since_last_commit ?? 0), 'a')">
            {{ commitsA.days_since_last_commit != null ? `${commitsA.days_since_last_commit}d` : '—' }}
          </div>
          <div :class="cellClass(lowerBetter(commitsA.days_since_last_commit ?? 0, commitsB.days_since_last_commit ?? 0), 'b')">
            {{ commitsB.days_since_last_commit != null ? `${commitsB.days_since_last_commit}d` : '—' }}
          </div>
        </div>
      </AppCard>
    </section>

    <!-- GitHub stats -->
    <section v-if="ghA && ghB" class="compare-panel__section">
      <h2 class="panel__title">GitHub</h2>
      <AppCard>
        <div class="compare-panel__metric-label">Stars</div>
        <div class="compare-panel__row">
          <div :class="cellClass(higherBetter(ghA.stars, ghB.stars), 'a')">{{ fmt(ghA.stars) }}</div>
          <div :class="cellClass(higherBetter(ghA.stars, ghB.stars), 'b')">{{ fmt(ghB.stars) }}</div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Forks</div>
        <div class="compare-panel__row">
          <div :class="cellClass(higherBetter(ghA.forks, ghB.forks), 'a')">{{ fmt(ghA.forks) }}</div>
          <div :class="cellClass(higherBetter(ghA.forks, ghB.forks), 'b')">{{ fmt(ghB.forks) }}</div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Open Issues</div>
        <div class="compare-panel__row">
          <div :class="cellClass(lowerBetter(ghA.open_issues, ghB.open_issues), 'a')">{{ fmt(ghA.open_issues) }}</div>
          <div :class="cellClass(lowerBetter(ghA.open_issues, ghB.open_issues), 'b')">{{ fmt(ghB.open_issues) }}</div>
        </div>
      </AppCard>
    </section>

    <!-- Structure -->
    <section v-if="structA && structB" class="compare-panel__section">
      <h2 class="panel__title">Project</h2>
      <AppCard>
        <div class="compare-panel__metric-label">Releases</div>
        <div class="compare-panel__row">
          <div :class="cellClass(higherBetter(structA.release_count, structB.release_count), 'a')">{{ fmt(structA.release_count) }}</div>
          <div :class="cellClass(higherBetter(structA.release_count, structB.release_count), 'b')">{{ fmt(structB.release_count) }}</div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Bus Factor</div>
        <div class="compare-panel__row">
          <div :class="cellClass(higherBetter(structA.bus_factor, structB.bus_factor), 'a')">{{ structA.bus_factor }}</div>
          <div :class="cellClass(higherBetter(structA.bus_factor, structB.bus_factor), 'b')">{{ structB.bus_factor }}</div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Total Files</div>
        <div class="compare-panel__row">
          <div class="compare-panel__cell">{{ fmt(structA.total_files) }}</div>
          <div class="compare-panel__cell">{{ fmt(structB.total_files) }}</div>
        </div>
      </AppCard>
    </section>

    <!-- Architecture -->
    <section v-if="graphA && graphB" class="compare-panel__section">
      <h2 class="panel__title">Architecture</h2>
      <AppCard>
        <div class="compare-panel__metric-label">God Modules</div>
        <div class="compare-panel__row">
          <div :class="cellClass(lowerBetter(graphA.god_modules.length, graphB.god_modules.length), 'a')">{{ graphA.god_modules.length }}</div>
          <div :class="cellClass(lowerBetter(graphA.god_modules.length, graphB.god_modules.length), 'b')">{{ graphB.god_modules.length }}</div>
        </div>

        <div class="compare-panel__metric-label" style="margin-top:0.75rem">Dependency Cycles</div>
        <div class="compare-panel__row">
          <div :class="cellClass(lowerBetter(graphA.cycle_count, graphB.cycle_count), 'a')">{{ graphA.cycle_count }}</div>
          <div :class="cellClass(lowerBetter(graphA.cycle_count, graphB.cycle_count), 'b')">{{ graphB.cycle_count }}</div>
        </div>
      </AppCard>
    </section>

    <!-- Dependencies -->
    <section v-if="depsA && depsB" class="compare-panel__section">
      <h2 class="panel__title">Dependencies</h2>
      <AppCard>
        <div class="compare-panel__metric-label">Total Dependencies</div>
        <div class="compare-panel__row">
          <div class="compare-panel__cell">{{ fmt(depsA.dependency_count) }}</div>
          <div class="compare-panel__cell">{{ fmt(depsB.dependency_count) }}</div>
        </div>
      </AppCard>
    </section>

    <!-- Tags -->
    <section v-if="clsA?.tags?.length || clsB?.tags?.length" class="compare-panel__section">
      <h2 class="panel__title">Tags</h2>
      <div class="compare-panel__row compare-panel__row--tags">
        <div class="compare-panel__tags">
          <AppBadge v-for="tag in (clsA?.tags ?? [])" :key="tag" variant="info" class="compare-panel__tag">
            {{ tag.replace(/-/g, ' ') }}
          </AppBadge>
          <span v-if="!clsA?.tags?.length" class="compare-panel__cell">—</span>
        </div>
        <div class="compare-panel__tags">
          <AppBadge v-for="tag in (clsB?.tags ?? [])" :key="tag" variant="info" class="compare-panel__tag">
            {{ tag.replace(/-/g, ' ') }}
          </AppBadge>
          <span v-if="!clsB?.tags?.length" class="compare-panel__cell">—</span>
        </div>
      </div>
    </section>

  </div>
</template>
