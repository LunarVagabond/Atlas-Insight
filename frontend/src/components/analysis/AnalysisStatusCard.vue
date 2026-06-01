<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import AppButton from '../ui/AppButton.vue'
import { useAnalysisStore } from '../../stores/analysis'
import type { AnalysisRun } from '../../stores/analysis'
import { techStackFromDeps } from '../../composables/frameworkSignals'

const props = defineProps<{ run: AnalysisRun }>()
const store = useAnalysisStore()
const router = useRouter()

function pluralize(n: number, word: string) {
  return `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`
}

function ageFromDate(isoDate: string): string {
  const created = new Date(isoDate)
  const years = Math.floor((Date.now() - created.getTime()) / (1000 * 60 * 60 * 24 * 365))
  if (years < 1) return 'less than a year old'
  return `${years} year${years === 1 ? '' : 's'} old`
}

const narrative = computed(() => {
  const r = props.run.result
  if (!r || r.error) return null
  const meta: Record<string, any> = r.github_meta ?? {}
  const cls: Record<string, any> = r.classification ?? {}
  const commits: Record<string, any> = r.commits ?? {}
  const structure: Record<string, any> = r.structure ?? {}

  const lang = meta.primary_language ? `${meta.primary_language} ` : ''
  const desc = meta.github_description ? (meta.github_description as string).replace(/\.$/, '') : null
  const health = cls.project_health?.label ?? null
  const difficulty = cls.contribution_difficulty?.label ?? null
  const contributors: number = commits.total_contributors ?? 0
  const totalCommits: number = commits.total_commits ?? 0
  const age = meta.created_at ? ageFromDate(meta.created_at as string) : null
  const busFactor: number | null = structure.bus_factor ?? null

  const sentences: string[] = []

  let s1 = `${lang}repository`
  if (desc) s1 += ` — ${desc}`
  if (age) s1 += `, ${age}`
  if (contributors > 0 && totalCommits > 0) {
    s1 += `, with ${pluralize(totalCommits, 'commit')} from ${pluralize(contributors, 'contributor')}`
  }
  sentences.push(s1.charAt(0).toUpperCase() + s1.slice(1) + '.')

  if (health || difficulty) {
    let s2 = ''
    if (health) s2 += `Scores ${health} on project health`
    if (difficulty) s2 += `${health ? ', rated ' : 'Contributions rated '}${difficulty} for new contributors`
    sentences.push(s2 + '.')
  }

  if (busFactor !== null) {
    if (busFactor <= 1) {
      sentences.push('Knowledge concentrated in very few contributors — high bus factor risk.')
    } else if (busFactor <= 3) {
      sentences.push(`Bus factor ${busFactor} — small core team carries most knowledge.`)
    } else {
      sentences.push(`Bus factor ${busFactor} — knowledge well-distributed across the team.`)
    }
  }

  return sentences
})

const techStack = computed(() => {
  if (props.run.result?.structure?.tech_stack?.length) {
    return props.run.result.structure.tech_stack
  }
  const deps = props.run.result?.dependencies?.dependencies ?? []
  return techStackFromDeps(deps)
})

const ossScore = computed(() => props.run.result?.oss_score ?? null)


const ossBadgeEmoji: Record<string, string> = {
  champion: '🏆',
  thriving: '⭐',
  growing: '🌱',
  seedling: '🌿',
  struggling: '😬',
  dormant: '💀',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

async function reanalyze() {
  const newRunId = await store.retryRun(props.run.id)
  router.push(`/results/${newRunId}`)
}

const cooldownUntil = computed(() => {
  const cu = props.run.cooldown_until
  if (!cu) return null
  const d = new Date(cu)
  return d > new Date() ? d : null
})

const cooldownLabel = computed(() => {
  if (!cooldownUntil.value) return null
  const diffMs = cooldownUntil.value.getTime() - Date.now()
  const hours = Math.floor(diffMs / 3_600_000)
  const mins = Math.floor((diffMs % 3_600_000) / 60_000)
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
})

const collapsed = ref(false)
</script>

<template>
  <AppCard>
    <div class="status-card">
      <button class="status-card__toggle" @click="collapsed = !collapsed">
        <span class="status-card__toggle-label">{{ run.repo_owner }}/{{ run.repo_name }}</span>
        <div v-if="run.result?.classification" class="cls-chips status-card__header-chips">
          <span class="cls-chips__chip cls-chips__chip--health" :title="`Project health: ${run.result.classification.project_health.label}`">Health: {{ run.result.classification.project_health.label }}</span>
          <span class="cls-chips__chip cls-chips__chip--difficulty" :title="`How easy it is to make your first contribution`">Contrib: {{ run.result.classification.contribution_difficulty.label }}</span>
          <span class="cls-chips__chip cls-chips__chip--complexity" :title="`Code complexity: ${run.result.classification.code_complexity.label}`">Code: {{ run.result.classification.code_complexity.label }}</span>
          <span class="cls-chips__chip cls-chips__chip--docs" :title="`Documentation grade: ${run.result.classification.documentation_grade.label}`">Docs: {{ run.result.classification.documentation_grade.label }}</span>
        </div>
        <span :class="['status-card__toggle-chevron', collapsed && 'status-card__toggle-chevron--collapsed']">▾</span>
      </button>
      <div v-show="!collapsed" class="status-card__main-row">
        <div class="status-card__meta">
          <div class="status-card__row">
            <span class="status-card__label">Author</span>
            <span class="status-card__value">{{ run.repo_owner }}</span>
          </div>
          <div v-if="run.result?.github_meta?.license_spdx ?? run.result?.structure?.license_type" class="status-card__row">
            <span class="status-card__label">License</span>
            <span class="status-card__value">{{ run.result?.github_meta?.license_spdx ?? run.result?.structure?.license_type }}</span>
          </div>
          <div class="status-card__row">
            <span class="status-card__label">Last Pulled</span>
            <span class="status-card__value">{{ run.last_fetched_at ? formatDate(run.last_fetched_at) : 'Never' }}</span>
          </div>
          <div v-if="narrative" class="status-card__narrative">
            <p v-for="(s, i) in narrative" :key="i" class="status-card__narrative-line">{{ s }}</p>
          </div>
          <div v-if="techStack.length" class="status-card__stack">
            <AppBadge v-for="t in techStack" :key="t" variant="info">{{ t }}</AppBadge>
          </div>
          <div v-if="run.is_stale" class="status-card__row">
            <span class="status-card__label">Freshness</span>
            <div class="status-card__stale">
              <AppBadge variant="warning">Stale</AppBadge>
              <AppButton v-if="!cooldownUntil" variant="secondary" @click="reanalyze">Refresh Project</AppButton>
              <span v-else class="cooldown-label" :title="`Re-analysis available in ${cooldownLabel}`">↻ in {{ cooldownLabel }}</span>
            </div>
          </div>
        </div>

        <div v-if="ossScore" :class="['status-card__oss', `status-card__oss--${ossScore.badge}`]">
          <span class="status-card__oss-heading">OSS Score</span>
          <div class="status-card__oss-main">
            <span class="status-card__oss-emoji">{{ ossBadgeEmoji[ossScore.badge] }}</span>
            <span class="status-card__oss-divider">|</span>
            <span class="status-card__oss-score">{{ ossScore.score.toFixed(1) }}<span class="status-card__oss-of">/10</span></span>
          </div>
          <span class="status-card__oss-label">{{ ossScore.label }}</span>
        </div>
      </div>
    </div>
  </AppCard>
</template>
