<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{ result: RunResult }>()

const { commits, heuristics, github_meta: gh, structure, classification: cls } = props.result

const overallScore = Math.round(
  heuristics.reduce((acc, h) => acc + h.score, 0) / (heuristics.length || 1)
)

function scoreVariant(score: number): 'completed' | 'warning' | 'failed' {
  if (score < 30) return 'completed'
  if (score < 60) return 'warning'
  return 'failed'
}

function formatStat(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

const topLanguages = computed(() => structure?.languages?.slice(0, 4) ?? [])

const langBarColors = ['#0969da', '#2da44e', '#e36209', '#8250df']
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Overview</h2>

    <!-- Key metrics -->
    <div class="panel__grid">
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ commits.total_commits.toLocaleString() }}</div>
          <div class="stat__label">Total Commits</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ commits.total_contributors }}</div>
          <div class="stat__label">Contributors</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ commits.days_since_last_commit ?? '—' }}</div>
          <div class="stat__label">Days Since Last Commit</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">
            <AppBadge :variant="scoreVariant(overallScore)">Risk: {{ overallScore }}/100</AppBadge>
          </div>
          <div class="stat__label">Overall Health Score</div>
        </div>
      </AppCard>
    </div>

    <!-- Abandoned warning -->
    <div v-if="commits.abandoned" style="margin-top: 1rem">
      <AppBadge variant="failed">Repository appears abandoned (no commits in 365+ days)</AppBadge>
    </div>

    <!-- Classification row -->
    <div v-if="cls" class="overview-classify">
      <div class="overview-classify__item">
        <span class="overview-classify__label">Contribution</span>
        <AppBadge
          :variant="['very_easy','easy'].includes(cls.contribution_difficulty.key) ? 'completed' : cls.contribution_difficulty.key === 'moderate' ? 'warning' : 'failed'"
        >
          {{ cls.contribution_difficulty.label }}
        </AppBadge>
      </div>
      <div class="overview-classify__item">
        <span class="overview-classify__label">Health</span>
        <AppBadge
          :variant="['thriving','active'].includes(cls.project_health.key) ? 'completed' : cls.project_health.key === 'stable' ? 'info' : cls.project_health.key === 'declining' ? 'warning' : 'failed'"
        >
          {{ cls.project_health.label }}
        </AppBadge>
      </div>
      <div class="overview-classify__item">
        <span class="overview-classify__label">Complexity</span>
        <AppBadge
          :variant="cls.code_complexity.key === 'simple' ? 'completed' : cls.code_complexity.key === 'moderate' ? 'info' : cls.code_complexity.key === 'complex' ? 'warning' : 'failed'"
        >
          {{ cls.code_complexity.label }}
        </AppBadge>
      </div>
      <div class="overview-classify__item">
        <span class="overview-classify__label">Docs</span>
        <AppBadge
          :variant="['excellent','good'].includes(cls.documentation_grade.key) ? 'completed' : ['fair'].includes(cls.documentation_grade.key) ? 'warning' : 'failed'"
        >
          {{ cls.documentation_grade.label }}
        </AppBadge>
      </div>
    </div>

    <!-- GitHub stats -->
    <div v-if="gh && (gh.stars || gh.forks)" class="overview-github">
      <span class="overview-github__stat">★ {{ formatStat(gh.stars) }} stars</span>
      <span class="overview-github__divider">·</span>
      <span class="overview-github__stat">⑂ {{ formatStat(gh.forks) }} forks</span>
      <span class="overview-github__divider">·</span>
      <span class="overview-github__stat">⚠ {{ formatStat(gh.open_issues) }} issues</span>
      <template v-if="gh.open_prs !== null">
        <span class="overview-github__divider">·</span>
        <span class="overview-github__stat">{{ gh.open_prs }} open PRs</span>
      </template>
      <template v-if="gh.license_name">
        <span class="overview-github__divider">·</span>
        <span class="overview-github__stat">{{ gh.license_spdx ?? gh.license_name }}</span>
      </template>
    </div>

    <!-- Language mini-bars -->
    <div v-if="topLanguages.length" class="overview-langs">
      <div
        v-for="(lang, idx) in topLanguages"
        :key="lang.name"
        class="overview-langs__bar"
        :style="{ width: `${lang.pct}%`, background: langBarColors[idx] }"
        :title="`${lang.name}: ${lang.pct}%`"
      />
      <div class="overview-langs__labels">
        <span
          v-for="(lang, idx) in topLanguages"
          :key="lang.name"
          class="overview-langs__label"
        >
          <span class="overview-langs__dot" :style="{ background: langBarColors[idx] }" />
          {{ lang.name }} {{ lang.pct }}%
        </span>
      </div>
    </div>
  </div>
</template>
