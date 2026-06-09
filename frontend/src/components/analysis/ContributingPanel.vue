<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import ContributionDrawer from './ContributionDrawer.vue'
import type { ArchTour, ContributionOpportunity, StructureData, TodoData } from '../../stores/analysis'
import type { CommitData } from '../../types/commits'
import type { GitHubMeta } from '../../types/github'

const props = defineProps<{
  opportunities: ContributionOpportunity[]
  repoUrl?: string
  structure?: StructureData
  todos?: TodoData
  archTours?: ArchTour[]
  commits?: CommitData
  isDocsOnly?: boolean
  githubMeta?: GitHubMeta
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

function renderMarkdown(text: string): string {
  const raw = marked.parse(text, { async: false }) as string
  return DOMPurify.sanitize(raw)
}

const githubCount = computed(() => props.opportunities.filter(o => o.category === 'github-issue' || o.category === 'feature').length)
const heuristicCount = computed(() => props.opportunities.filter(o => o.category !== 'github-issue' && o.category !== 'feature').length)

const issuesUrl = computed(() => props.repoUrl ? `${props.repoUrl}/issues` : null)
const pullsUrl = computed(() => props.repoUrl ? `${props.repoUrl}/pulls` : null)

const docsDescription = computed(() => props.githubMeta?.github_description ?? null)
const docsTopics = computed(() => props.githubMeta?.topics ?? [])
const docsStars = computed(() => props.githubMeta?.stars ?? null)
const docsHomepage = computed(() => props.githubMeta?.homepage ?? null)
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Contributing</h2>

    <!-- ── Docs-only: prose view ─────────────────────────────────────── -->
    <template v-if="isDocsOnly">
      <div class="docs-contrib">
        <p v-if="docsDescription" class="docs-contrib__about">{{ docsDescription }}</p>

        <div v-if="docsTopics.length" class="docs-contrib__topics">
          <span v-for="topic in docsTopics" :key="topic" class="docs-contrib__topic">{{ topic }}</span>
        </div>

        <div class="docs-contrib__body">
          <p>This is a documentation or curated-list repository — there's no application code to patch. The best contributions here are content, not code.</p>
          <p>If you know a tool, library, article, or resource that belongs on this list and isn't already there, a pull request is the right move. Keep the PR focused: one item or a small batch of related items, with a brief note on why it fits.</p>
          <p v-if="docsHomepage">The project's homepage is <a :href="docsHomepage" target="_blank" rel="noopener noreferrer" class="docs-contrib__link">{{ docsHomepage }} ↗</a> — check there for any submission guidelines before opening a PR.</p>
          <p v-else>Check the README for any submission guidelines before opening a PR — many curated lists have specific formatting requirements.</p>
          <p v-if="docsStars !== null && docsStars > 1000">With {{ docsStars.toLocaleString() }} stars this list is widely referenced. High-quality additions get merged regularly.</p>
        </div>

        <div v-if="repoUrl" class="contrib-links" style="margin-top: 1.5rem">
          <a :href="issuesUrl!" target="_blank" rel="noopener noreferrer" class="contrib-links__link">
            🐛 Open Issues ↗
          </a>
          <a :href="pullsUrl!" target="_blank" rel="noopener noreferrer" class="contrib-links__link">
            ⊞ Open PRs ↗
          </a>
        </div>

        <!-- Commit conventions still useful for docs repos -->
        <div v-if="conventions && conventions.style !== 'mixed'" class="contrib-conventions" style="margin-top: 1.5rem">
          <h3 class="contrib-conventions__title">Commit Conventions</h3>
          <div v-if="conventions.format_template" class="contrib-conventions__template-block">
            <span class="contrib-conventions__template-label">Commit format</span>
            <code class="contrib-conventions__template">{{ conventions.format_template }}</code>
            <span class="contrib-conventions__template-sub">
              {{ STYLE_LABELS[conventions.style] ?? conventions.style }} · {{ Math.round(conventions.style_confidence * 100) }}% of commits follow this pattern
            </span>
          </div>
          <div v-if="conventions.examples.length" class="contrib-conventions__examples">
            <span class="contrib-conventions__examples-label">Example</span>
            <code class="contrib-conventions__example">{{ conventions.examples[0] }}</code>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Normal code repo view ─────────────────────────────────────── -->
    <template v-else>

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
        <span class="contrib-conventions__examples-label">Example</span>
        <code class="contrib-conventions__example">{{ conventions.examples[0] }}</code>
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
            <p class="contrib-card__desc" v-html="renderMarkdown(opp.description)"></p>

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
            <p class="contrib-card__desc" v-html="renderMarkdown(opp.description)"></p>
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
            <p class="contrib-card__desc" v-html="renderMarkdown(opp.description)"></p>
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

    <ContributionDrawer :opportunity="activeOpp" :arch-tours="archTours" :repo-url="repoUrl" @close="activeOpp = null" />

    </template>
  </div>
</template>
