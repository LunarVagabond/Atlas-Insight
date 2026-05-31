<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppBadge from '../ui/AppBadge.vue'
import AppButton from '../ui/AppButton.vue'

interface SpotlightData {
  run_id: string
  repo_url: string
  repo_owner: string
  repo_name: string
  week_start: string
  stars: number | null
  health_label: string | null
  health_key: string | null
  primary_language: string | null
  topics: string[]
  github_description: string | null
  pick_number: number
}

const props = defineProps<{ spotlight: SpotlightData }>()
const router = useRouter()

type BadgeVariant = 'pending' | 'running' | 'completed' | 'failed' | 'warning' | 'info'

const HEALTH_COLORS: Record<string, BadgeVariant> = {
  thriving: 'completed',
  active: 'completed',
  stable: 'warning',
  declining: 'failed',
  abandoned: 'failed',
}

const weekLabel = computed(() => {
  const d = new Date(props.spotlight.week_start + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
})

const pickLabel = computed(() => {
  const n = props.spotlight.pick_number
  if (n === 1) return 'First spotlight'
  const suffixes: Record<number, string> = { 1: 'st', 2: 'nd', 3: 'rd' }
  const s = suffixes[n % 10] && n % 100 !== 11 && n % 100 !== 12 && n % 100 !== 13
    ? suffixes[n % 10]
    : 'th'
  return `${n}${s} time in the spotlight`
})
</script>

<template>
  <div class="rotw-card">
    <div class="rotw-card__eyebrow">Repo of the Week</div>
    <div class="rotw-card__week">Week of {{ weekLabel }}</div>
    <span class="rotw-card__pick-badge">{{ pickLabel }}</span>
    <div class="rotw-card__content">
      <div class="rotw-card__left">
        <h3 class="rotw-card__name">
          <a :href="spotlight.repo_url" target="_blank" rel="noopener noreferrer">
            {{ spotlight.repo_owner }}/{{ spotlight.repo_name }} ↗
          </a>
        </h3>
        <p v-if="spotlight.github_description" class="rotw-card__desc">
          {{ spotlight.github_description }}
        </p>
        <div class="rotw-card__meta">
          <span v-if="spotlight.primary_language" class="rotw-card__lang">
            {{ spotlight.primary_language }}
          </span>
          <span v-if="spotlight.stars !== null" class="rotw-card__stars">
            ★ {{ spotlight.stars?.toLocaleString() }}
          </span>
          <AppBadge
            v-if="spotlight.health_label && spotlight.health_key"
            :variant="(HEALTH_COLORS[spotlight.health_key] ?? 'info') as BadgeVariant"
          >
            {{ spotlight.health_label }}
          </AppBadge>
        </div>
        <div v-if="spotlight.topics.length" class="rotw-card__topics">
          <span v-for="t in spotlight.topics.slice(0, 5)" :key="t" class="rotw-card__topic">
            {{ t }}
          </span>
        </div>
      </div>
      <div class="rotw-card__action">
        <AppButton variant="primary" @click="router.push(`/results/${spotlight.run_id}`)">
          Read the story →
        </AppButton>
      </div>
    </div>
  </div>
</template>
