<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GitHubContributor, OwnershipData, OwnershipSubsystem, JitIssue } from '../../stores/analysis'
import FileHistoryDrawer from './FileHistoryDrawer.vue'

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
  const name = author.split('@')[0]
  const parts = name.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
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

const activeHint = ref<string | null>(null)
function toggleHint(e: Event, key: string) {
  e.stopPropagation()
  activeHint.value = activeHint.value === key ? null : key
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Repository Ownership</h2>
    <p class="ownership-intro">
      Which areas of this codebase are most active, and who works on them.
      <span v-if="ownership.bus_factor > 0">
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
        <img :src="c.avatar_url" :alt="c.login" class="ownership-contributor__avatar" />
        <div class="ownership-contributor__info">
          <span class="ownership-contributor__name">{{ c.login }}</span>
          <span class="ownership-contributor__files">{{ c.contributions.toLocaleString() }} commits</span>
        </div>
      </a>
    </div>
    <!-- Fallback: git-based contributors (no GitHub data) -->
    <div v-else-if="ownership.top_contributors.length" class="ownership-contributors">
      <div v-for="c in ownership.top_contributors.slice(0, 8)" :key="c.author" class="ownership-contributor" :title="c.author">
        <div class="ownership-contributor__initials">{{ contributorInitials(c.author) }}</div>
        <div class="ownership-contributor__info">
          <span class="ownership-contributor__name">{{ c.author.split('@')[0] }}</span>
          <span class="ownership-contributor__files">{{ c.files_touched }} files</span>
        </div>
      </div>
    </div>

    <!-- Subsystem cards -->
    <div v-if="sortedSubsystems.length" class="ownership-grid">
      <div v-for="sub in sortedSubsystems" :key="sub.id" class="ownership-card">
        <div class="ownership-card__header">
          <span class="ownership-card__icon">{{ SUBSYSTEM_ICONS[sub.subsystem_type] ?? '📁' }}</span>
          <div class="ownership-card__header-text">
            <span class="ownership-card__name">{{ sub.name }}</span>
            <div class="ownership-card__badges">
              <span class="ownership-card__file-count">{{ sub.file_count }} files</span>
              <span v-if="sub.primary_language" class="ownership-card__lang">{{ sub.primary_language }}</span>
            </div>
          </div>
        </div>

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
            <button v-if="runId" class="file-history-btn" :title="`View commit history for ${hf.file}`" @click="openFileHistory(hf.file)">📜</button>
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
