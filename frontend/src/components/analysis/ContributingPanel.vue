<script setup lang="ts">
import { computed, ref } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import ContributionDrawer from './ContributionDrawer.vue'
import ContributionPathPanel from './ContributionPathPanel.vue'
import type { ArchTour, ContributionOpportunity, StructureData, TodoData } from '../../stores/analysis'
import type { CommitData } from '../../types/commits'

const props = defineProps<{
  opportunities: ContributionOpportunity[]
  repoUrl?: string
  structure?: StructureData
  todos?: TodoData
  archTours?: ArchTour[]
  commits?: CommitData
}>()

const STYLE_LABELS: Record<string, string> = {
  conventional_commits: 'Conventional Commits',
  ticket_prefix: 'Ticket / Issue Prefix',
  bracket_prefix: 'Bracket Prefix',
  emoji_prefix: 'Emoji Prefix',
  sentence_case: 'Sentence Case',
  mixed: 'Mixed / No Clear Standard',
}

const conventions = computed(() => props.commits?.commit_conventions ?? null)

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

function readinessVariant(label: string) {
  return label === 'Ready' ? 'completed' : label === 'Approachable' ? 'warning' : 'failed'
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
      <div class="contrib-signals__item" title="TODO, FIXME, HACK and similar comments left by developers as reminders to fix or improve code">
        <span class="contrib-signals__count">{{ todos.total }}</span>
        <span class="contrib-signals__label">TODO/FIXME comments found</span>
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

    <!-- Commit conventions -->
    <div v-if="conventions && conventions.style !== 'mixed'" class="contrib-conventions">
      <h3 class="contrib-conventions__title">Commit Conventions</h3>

      <div v-if="conventions.format_template" class="contrib-conventions__template-block">
        <span class="contrib-conventions__template-label">Commit format</span>
        <code class="contrib-conventions__template">{{ conventions.format_template }}</code>
        <span class="contrib-conventions__template-sub">
          {{ STYLE_LABELS[conventions.style] ?? conventions.style }} · {{ Math.round(conventions.style_confidence * 100) }}% of commits follow this pattern
        </span>
      </div>

      <div v-if="conventions.examples.length" class="contrib-conventions__examples">
        <span class="contrib-conventions__examples-label">Real examples</span>
        <code v-for="(ex, i) in conventions.examples" :key="i" class="contrib-conventions__example">{{ ex }}</code>
      </div>

      <div class="contrib-conventions__grid">
        <div class="contrib-conventions__stat">
          <span class="contrib-conventions__stat-label">Avg subject length</span>
          <span class="contrib-conventions__stat-value">{{ conventions.avg_subject_length }} chars</span>
          <span class="contrib-conventions__stat-sub">{{ Math.round(conventions.subject_under_72_pct * 100) }}% under 72</span>
        </div>
        <div v-if="conventions.issue_ref_rate >= 0.2" class="contrib-conventions__stat">
          <span class="contrib-conventions__stat-label">Issue references</span>
          <span class="contrib-conventions__stat-value">{{ Math.round(conventions.issue_ref_rate * 100) }}%</span>
          <span class="contrib-conventions__stat-sub">of commits link an issue</span>
        </div>
      </div>
    </div>

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
        <span class="contrib-section__title">🟢 Good starting points for new contributors</span>
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
            <AppBadge v-if="opp.readiness_label" :variant="readinessVariant(opp.readiness_label)">{{ opp.readiness_label }}</AppBadge>
            <span class="contrib-card__category">{{ CATEGORY_LABELS[opp.category] }}</span>
          </div>
        </AppCard>
      </div>
    </section>

    <!-- Intermediate -->
    <section v-if="intermediate.length" class="contrib-section">
      <div class="contrib-section__header">
        <span class="contrib-section__title">🟡 Requires some codebase familiarity</span>
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
            <AppBadge v-if="opp.readiness_label" :variant="readinessVariant(opp.readiness_label)">{{ opp.readiness_label }}</AppBadge>
            <span class="contrib-card__category">{{ CATEGORY_LABELS[opp.category] }}</span>
          </div>
        </AppCard>
      </div>
    </section>

    <!-- Advanced -->
    <section v-if="advanced.length" class="contrib-section">
      <div class="contrib-section__header">
        <span class="contrib-section__title">🔴 Complex — best after you've contributed a few times</span>
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
            <AppBadge v-if="opp.readiness_label" :variant="readinessVariant(opp.readiness_label)">{{ opp.readiness_label }}</AppBadge>
            <span class="contrib-card__category">{{ CATEGORY_LABELS[opp.category] }}</span>
          </div>
        </AppCard>
      </div>
    </section>

    <div v-if="!filtered.length" class="empty-state">
      No opportunities found for this filter.
    </div>

    <!-- Contribution Path Generator -->
    <ContributionPathPanel
      v-if="archTours?.length"
      :tours="archTours"
      :opportunities="opportunities"
      :repo-url="repoUrl"
      :all-files="structure?.all_files"
      style="margin-top: 2rem"
    />

    <ContributionDrawer :opportunity="activeOpp" :arch-tours="archTours" :repo-url="repoUrl" @close="activeOpp = null" />
  </div>
</template>
