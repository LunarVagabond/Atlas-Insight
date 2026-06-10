<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GitHubContributor, OwnershipData, OwnershipSubsystem } from '../../stores/analysis'
import type { JitIssue } from '../../types/jit'
import FileHistoryDrawer from './FileHistoryDrawer.vue'
import PrImpactCard from './PrImpactCard.vue'
import { EXTERNAL_IMG_ATTRS } from '../../utils/externalImage'

const props = defineProps<{
  ownership: OwnershipData
  jitIssues: JitIssue[] | null
  jitLoading: boolean
  repoUrl?: string
  githubContributors?: GitHubContributor[]
  runId?: string
}>()

const activeFilePath = ref<string | null>(null)
function openFileHistory(file: string) { activeFilePath.value = file }

const SUBSYSTEM_ICONS: Record<string, string> = {
  frontend: '🖥',
  api: '🔌',
  data: '🗄',
  tests: '🧪',
  config: '⚙️',
  docs: '📚',
  overview: '🗺',
  other: '📁',
}

const SUBSYSTEM_KEYWORDS: Record<string, string[]> = {
  frontend: ['ui', 'component', 'page', 'view', 'style', 'css', 'layout', 'render', 'display'],
  api: ['api', 'endpoint', 'route', 'handler', 'request', 'response', 'controller'],
  data: ['model', 'schema', 'migration', 'database', 'query', 'db', 'orm'],
  tests: ['test', 'spec', 'coverage', 'assertion', 'mock', 'fixture'],
  config: ['config', 'ci', 'deploy', 'pipeline', 'workflow', 'docker', 'k8s'],
}

function subsystemIssues(sub: OwnershipSubsystem): JitIssue[] {
  if (!props.jitIssues) return []
  const keywords = SUBSYSTEM_KEYWORDS[sub.subsystem_type] ?? []
  if (!keywords.length) return []
  return props.jitIssues.filter(issue => {
    const text = issue.title.toLowerCase()
    return keywords.some(kw => text.includes(kw))
  })
}

function contributorInitials(author: string): string {
  const parts = author.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return author.slice(0, 2).toUpperCase()
}

function githubFileUrl(file: string): string | null {
  if (!props.repoUrl) return null
  return `${props.repoUrl}/blob/HEAD/${file}`
}

const sortedSubsystems = computed(() =>
  [...props.ownership.subsystems].sort((a, b) => b.activity_score - a.activity_score)
)

const topContributors = computed(() =>
  props.githubContributors?.length
    ? props.githubContributors.slice(0, 8)
    : null
)

const isSolo = computed(() => {
  const count = props.githubContributors?.length ?? props.ownership.top_contributors.length
  return count <= 1
})

const activeHint = ref<string | null>(null)
function toggleHint(e: Event, key: string) {
  e.stopPropagation()
  activeHint.value = activeHint.value === key ? null : key
}

const expandedSubsystems = ref<Set<string>>(new Set())

function toggleSubsystem(id: string) {
  const next = new Set(expandedSubsystems.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedSubsystems.value = next
}

function isExpanded(id: string) {
  return expandedSubsystems.value.has(id)
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Repository Ownership</h2>
    <p class="ownership-intro">
      Which areas of this codebase are most active, and who works on them.
      <span v-if="ownership.bus_factor > 0 && !isSolo">
        <strong>Knowledge risk:</strong> only <strong>{{ ownership.bus_factor }}</strong>
        contributor{{ ownership.bus_factor !== 1 ? 's' : '' }} account for 80% of the codebase —
        if they left, progress could slow significantly.
      </span>
    </p>

    <!-- Global contributors (GitHub data) -->
    <div v-if="topContributors?.length" class="ownership-contributors">
      <a
        v-for="c in topContributors"
        :key="c.login"
        :href="c.html_url"
        target="_blank"
        rel="noopener noreferrer"
        class="ownership-contributor ownership-contributor--link"
        :title="`View ${c.login}'s GitHub profile`"
      >
        <img
          :src="c.avatar_url"
          :alt="c.login"
          class="ownership-contributor__avatar"
          v-bind="EXTERNAL_IMG_ATTRS"
        />
        <div class="ownership-contributor__info">
          <span class="ownership-contributor__name">{{ c.login }}</span>
          <span class="ownership-contributor__files">{{ c.contributions.toLocaleString() }} commits</span>
        </div>
      </a>
    </div>
    <!-- Fallback: git-based contributors (no GitHub data) -->
    <div v-else-if="ownership.top_contributors.length" class="ownership-contributors">
      <div v-for="c in ownership.top_contributors.slice(0, 8)" :key="c.author" class="ownership-contributor" :title="c.email ?? c.author">
        <div class="ownership-contributor__initials">{{ contributorInitials(c.author) }}</div>
        <div class="ownership-contributor__info">
          <span class="ownership-contributor__name">{{ c.author }}</span>
          <span class="ownership-contributor__files">{{ c.files_touched }} files touched</span>
        </div>
      </div>
    </div>

    <PrImpactCard
      v-if="runId"
      :run-id="runId"
      :repo-url="repoUrl"
      style="margin-bottom: 1.5rem"
    />

    <!-- Subsystem cards -->
    <div v-if="sortedSubsystems.length" class="ownership-grid">
      <div
        v-for="sub in sortedSubsystems"
        :key="sub.id"
        class="ownership-card"
        :class="{ 'ownership-card--expanded': isExpanded(sub.id) }"
      >
        <button
          type="button"
          class="ownership-card__header ownership-card__header--toggle"
          :aria-expanded="isExpanded(sub.id)"
          @click="toggleSubsystem(sub.id)"
        >
          <span class="ownership-card__icon">{{ SUBSYSTEM_ICONS[sub.subsystem_type] ?? '📁' }}</span>
          <div class="ownership-card__header-text">
            <span class="ownership-card__name">{{ sub.name }}</span>
            <div class="ownership-card__badges">
              <span class="ownership-card__file-count">{{ sub.file_count }} files</span>
              <span v-if="sub.primary_language" class="ownership-card__lang">{{ sub.primary_language }}</span>
              <span class="ownership-card__activity-chip">{{ Math.round(sub.activity_score * 100) }}% activity</span>
            </div>
          </div>
          <span class="ownership-card__chevron">{{ isExpanded(sub.id) ? '▾' : '▸' }}</span>
        </button>

        <div v-show="isExpanded(sub.id)" class="ownership-card__body">
        <!-- Activity bar -->
        <div class="ownership-activity-bar" :title="`${Math.round(sub.activity_score * 100)}% of all recent git commits happened in this area`">
          <div class="ownership-activity-bar__fill" :style="{ width: `${Math.min(sub.activity_score * 100, 100)}%` }" />
        </div>
        <span class="ownership-activity-bar__label">{{ Math.round(sub.activity_score * 100) }}% of all recent code changes happened here</span>

        <!-- Most-changed files -->
        <div v-if="sub.hot_files.length" class="ownership-card__section">
          <div class="ownership-card__section-row">
            <span class="ownership-card__section-title">Most-changed files</span>
            <button class="card-hint-btn" :class="{ 'card-hint-btn--active': activeHint === sub.id + '_hotfiles' }" @click="toggleHint($event, sub.id + '_hotfiles')">?</button>
          </div>
          <Transition name="hint-expand">
            <p v-if="activeHint === sub.id + '_hotfiles'" class="card-hint-text">Files with the most git commits — often where active development or known bugs live. High commit counts mean lots of change, which can signal importance or instability.</p>
          </Transition>
          <div v-for="hf in sub.hot_files.slice(0, 3)" :key="hf.file" class="ownership-hot-file">
            <a
              v-if="githubFileUrl(hf.file)"
              :href="githubFileUrl(hf.file)!"
              target="_blank"
              rel="noopener noreferrer"
              class="ownership-hot-file__link"
              :title="hf.file"
            >{{ hf.file.split('/').pop() }}</a>
            <code v-else class="ownership-hot-file__code">{{ hf.file.split('/').pop() }}</code>
            <span class="ownership-hot-file__count" :title="`Changed ${hf.commit_count} times in git history`">{{ hf.commit_count }} commits</span>
            <button v-if="runId" class="file-history-btn" :title="`View commit history for ${hf.file}`" @click="openFileHistory(hf.file)"><svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg></button>
          </div>
        </div>

        <!-- Core file warning -->
        <div v-if="sub.god_modules.length" class="ownership-card__god-warning">
          ⚠ {{ sub.god_modules.length }} core file{{ sub.god_modules.length !== 1 ? 's' : '' }} imported everywhere — changes here could affect many other parts of the project
        </div>

        <!-- JIT issues -->
        <div class="ownership-card__section">
          <span class="ownership-card__section-title">Open issues</span>
          <template v-if="jitLoading">
            <span class="ownership-card__jit-loading">Loading…</span>
          </template>
          <template v-else-if="jitIssues === null">
            <span class="ownership-card__jit-unavailable">Could not load GitHub issues</span>
          </template>
          <template v-else>
            <div v-if="subsystemIssues(sub).length" class="ownership-card__issues">
              <a
                v-for="issue in subsystemIssues(sub).slice(0, 3)"
                :key="issue.number"
                :href="issue.url"
                target="_blank"
                rel="noopener noreferrer"
                class="ownership-issue-link"
              >
                <span class="ownership-issue-link__num">#{{ issue.number }}</span>
                <span class="ownership-issue-link__title">{{ issue.title }}</span>
              </a>
            </div>
            <span v-else class="ownership-card__jit-unavailable">No matching open issues</span>
          </template>
        </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      No subsystem data available — re-analyze the repository to generate ownership signals.
    </div>


    <FileHistoryDrawer
      :run-id="runId ?? null"
      :path="activeFilePath"
      :repo-url="repoUrl"
      @close="activeFilePath = null"
    />
  </div>
</template>
