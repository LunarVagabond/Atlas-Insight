<script setup lang="ts">
import { computed, ref } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import ContributionDrawer from './ContributionDrawer.vue'
import type { ContributionOpportunity, StructureData, TodoData } from '../../stores/analysis'

const props = defineProps<{
  opportunities: ContributionOpportunity[]
  repoUrl?: string
  structure?: StructureData
  todos?: TodoData
}>()

type CategoryFilter = 'all' | ContributionOpportunity['category']
const activeFilter = ref<CategoryFilter>('all')

const CATEGORY_ICONS: Record<ContributionOpportunity['category'], string> = {
  documentation: '📝',
  testing: '🧪',
  ci: '⚙️',
  community: '🤝',
  refactoring: '🔧',
  security: '🔒',
  dependencies: '📦',
  'github-issue': '🐛',
  feature: '✨',
}

const CATEGORY_LABELS: Record<ContributionOpportunity['category'], string> = {
  documentation: 'Documentation',
  testing: 'Testing',
  ci: 'CI/CD',
  community: 'Community',
  refactoring: 'Refactoring',
  security: 'Security',
  dependencies: 'Dependencies',
  'github-issue': 'GitHub Issues',
  feature: 'Feature Requests',
}

const FILTERS: { key: CategoryFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'feature', label: 'Features' },
  { key: 'github-issue', label: 'Issues' },
  { key: 'documentation', label: 'Docs' },
  { key: 'testing', label: 'Testing' },
  { key: 'ci', label: 'CI/CD' },
  { key: 'community', label: 'Community' },
  { key: 'security', label: 'Security' },
  { key: 'dependencies', label: 'Dependencies' },
  { key: 'refactoring', label: 'Refactoring' },
]

const filtered = computed(() =>
  activeFilter.value === 'all'
    ? props.opportunities
    : props.opportunities.filter(o => o.category === activeFilter.value)
)

const beginner = computed(() => filtered.value.filter(o => o.difficulty === 'beginner'))
const intermediate = computed(() => filtered.value.filter(o => o.difficulty === 'intermediate'))
const advanced = computed(() => filtered.value.filter(o => o.difficulty === 'advanced'))

function diffVariant(d: ContributionOpportunity['difficulty']) {
  return d === 'beginner' ? 'completed' : d === 'intermediate' ? 'warning' : 'failed'
}

function riskVariant(r: ContributionOpportunity['risk']) {
  return r === 'low' ? 'completed' : r === 'medium' ? 'warning' : 'failed'
}

const availableFilters = computed(() =>
  FILTERS.filter(f => {
    if (f.key === 'all') return true
    return props.opportunities.some(o => o.category === f.key)
  })
)

const activeOpp = ref<ContributionOpportunity | null>(null)

const githubCount = computed(() => props.opportunities.filter(o => o.category === 'github-issue' || o.category === 'feature').length)
const heuristicCount = computed(() => props.opportunities.filter(o => o.category !== 'github-issue' && o.category !== 'feature').length)

const issuesUrl = computed(() => props.repoUrl ? `${props.repoUrl}/issues` : null)
const pullsUrl = computed(() => props.repoUrl ? `${props.repoUrl}/pulls` : null)
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Contributing Entry Points</h2>

    <!-- Quick links to GitHub -->
    <div v-if="repoUrl" class="contrib-links">
      <a :href="issuesUrl!" target="_blank" rel="noopener noreferrer" class="contrib-links__link">
        🐛 Open Issues ↗
      </a>
      <a :href="pullsUrl!" target="_blank" rel="noopener noreferrer" class="contrib-links__link">
        ⊞ Open PRs ↗
      </a>
    </div>

    <div v-if="todos?.total" class="contrib-signals">
      <div class="contrib-signals__item">
        <span class="contrib-signals__count">{{ todos.total }}</span>
        <span class="contrib-signals__label">code markers</span>
      </div>
      <template v-for="(count, type) in todos.by_type" :key="type">
        <div v-if="count > 0" class="contrib-signals__item">
          <code class="contrib-signals__type">{{ type }}</code>
          <span class="contrib-signals__type-count">{{ count }}</span>
        </div>
      </template>
    </div>

    <p class="contrib-summary">
      <strong>{{ opportunities.length }}</strong> recommended starting points
      <template v-if="heuristicCount && githubCount">
        — {{ heuristicCount }} from code analysis, {{ githubCount }} from open GitHub issues
      </template>
    </p>

    <!-- Category filter -->
    <div v-if="availableFilters.length > 2" class="table-filter-bar">
      <div class="table-filter-bar__group">
        <button
          v-for="f in availableFilters"
          :key="f.key"
          :class="['table-filter-bar__btn', activeFilter === f.key && 'table-filter-bar__btn--active']"
          @click="activeFilter = f.key"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <!-- Beginner -->
    <section v-if="beginner.length" class="contrib-section">
      <div class="contrib-section__header">
        <span class="contrib-section__title">🟢 Beginner Friendly</span>
        <span class="contrib-section__count">{{ beginner.length }}</span>
      </div>
      <div class="contrib-grid">
        <AppCard
          v-for="opp in beginner"
          :key="opp.id"
          class="contrib-card"
          style="cursor:pointer"
          @click="activeOpp = opp"
        >
          <div class="contrib-card__body">
            <div class="contrib-card__header">
              <span class="contrib-card__icon">{{ CATEGORY_ICONS[opp.category] }}</span>
              <span class="contrib-card__title">{{ opp.title }}</span>
            </div>
            <p class="contrib-card__desc">{{ opp.description }}</p>

            <!-- GitHub issue / feature extras -->
            <div v-if="opp.issue_url" class="contrib-card__issue-meta">
              <a
                v-if="opp.issue_url"
                :href="opp.issue_url"
                target="_blank"
                rel="noopener noreferrer"
                class="contrib-card__issue-link"
              >
                #{{ opp.issue_number }} ↗
              </a>
              <AppBadge v-if="opp.has_open_pr" variant="info" class="contrib-card__pr-badge">
                PR in progress
              </AppBadge>
              <AppBadge
                v-for="label in (opp.labels ?? []).slice(0, 3)"
                :key="label"
                variant="info"
                class="contrib-card__label-badge"
              >
                {{ label }}
              </AppBadge>
            </div>
          </div>
          <div class="contrib-card__footer">
            <AppBadge :variant="diffVariant(opp.difficulty)">{{ opp.difficulty }}</AppBadge>
            <AppBadge :variant="riskVariant(opp.risk)">{{ opp.risk }} risk</AppBadge>
            <span class="contrib-card__category">{{ CATEGORY_LABELS[opp.category] }}</span>
          </div>
        </AppCard>
      </div>
    </section>

    <!-- Intermediate -->
    <section v-if="intermediate.length" class="contrib-section">
      <div class="contrib-section__header">
        <span class="contrib-section__title">🟡 Intermediate</span>
        <span class="contrib-section__count">{{ intermediate.length }}</span>
      </div>
      <div class="contrib-grid">
        <AppCard
          v-for="opp in intermediate"
          :key="opp.id"
          class="contrib-card"
          style="cursor:pointer"
          @click="activeOpp = opp"
        >
          <div class="contrib-card__body">
            <div class="contrib-card__header">
              <span class="contrib-card__icon">{{ CATEGORY_ICONS[opp.category] }}</span>
              <span class="contrib-card__title">{{ opp.title }}</span>
            </div>
            <p class="contrib-card__desc">{{ opp.description }}</p>
            <div v-if="opp.category === 'github-issue'" class="contrib-card__issue-meta">
              <a
                v-if="opp.issue_url"
                :href="opp.issue_url"
                target="_blank"
                rel="noopener noreferrer"
                class="contrib-card__issue-link"
              >
                #{{ opp.issue_number }} ↗
              </a>
              <AppBadge v-if="opp.has_open_pr" variant="info" class="contrib-card__pr-badge">PR in progress</AppBadge>
              <AppBadge
                v-for="label in (opp.labels ?? []).slice(0, 3)"
                :key="label"
                variant="info"
                class="contrib-card__label-badge"
              >
                {{ label }}
              </AppBadge>
            </div>
          </div>
          <div class="contrib-card__footer">
            <AppBadge :variant="diffVariant(opp.difficulty)">{{ opp.difficulty }}</AppBadge>
            <AppBadge :variant="riskVariant(opp.risk)">{{ opp.risk }} risk</AppBadge>
            <span class="contrib-card__category">{{ CATEGORY_LABELS[opp.category] }}</span>
          </div>
        </AppCard>
      </div>
    </section>

    <!-- Advanced -->
    <section v-if="advanced.length" class="contrib-section">
      <div class="contrib-section__header">
        <span class="contrib-section__title">🔴 Advanced</span>
        <span class="contrib-section__count">{{ advanced.length }}</span>
      </div>
      <div class="contrib-grid">
        <AppCard
          v-for="opp in advanced"
          :key="opp.id"
          class="contrib-card"
          style="cursor:pointer"
          @click="activeOpp = opp"
        >
          <div class="contrib-card__body">
            <div class="contrib-card__header">
              <span class="contrib-card__icon">{{ CATEGORY_ICONS[opp.category] }}</span>
              <span class="contrib-card__title">{{ opp.title }}</span>
            </div>
            <p class="contrib-card__desc">{{ opp.description }}</p>
          </div>
          <div class="contrib-card__footer">
            <AppBadge :variant="diffVariant(opp.difficulty)">{{ opp.difficulty }}</AppBadge>
            <AppBadge :variant="riskVariant(opp.risk)">{{ opp.risk }} risk</AppBadge>
            <span class="contrib-card__category">{{ CATEGORY_LABELS[opp.category] }}</span>
          </div>
        </AppCard>
      </div>
    </section>

    <div v-if="!filtered.length" class="empty-state">
      No opportunities found for this filter.
    </div>

    <ContributionDrawer :opportunity="activeOpp" @close="activeOpp = null" />
  </div>
</template>
