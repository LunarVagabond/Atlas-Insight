<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { RunResult } from '../../stores/analysis'
import { useTableFilter } from '../../composables/useTableFilter'

const props = defineProps<{ result: RunResult }>()

const { readme, structure, security, github_meta: gh, classification: cls } = props.result

const hotFilesSource = computed(() => (structure?.hot_files ?? []) as Record<string, unknown>[])
const hotFilesFilter = useTableFilter(hotFilesSource, ['file'], 'commit_count', 'desc')

// Community file viewer
const expandedFile = ref<string | null>(null)

function toggleFile(key: string) {
  expandedFile.value = expandedFile.value === key ? null : key
}

function fileContent(key: string): string | null {
  if (key === 'readme') return readme?.content ?? null
  return structure?.community_files_content?.[key as keyof typeof structure.community_files_content] ?? null
}

function isMarkdown(key: string): boolean {
  return key === 'readme'
}

function renderMarkdown(md: string): string {
  return marked.parse(md) as string
}

const description = computed(() =>
  gh?.github_description || readme?.description || null
)

const repoAge = computed(() => {
  const days = structure?.repo_age_days
  if (!days) return null
  if (days < 365) return `${days} days`
  const years = (days / 365).toFixed(1)
  return `${years} years`
})

const lastReleaseAge = computed(() => {
  if (!structure?.last_release) return null
  const date = new Date(structure.last_release.date)
  const days = Math.floor((Date.now() - date.getTime()) / 86400000)
  if (days < 30) return `${days}d ago`
  if (days < 365) return `${Math.floor(days / 30)}mo ago`
  return `${(days / 365).toFixed(1)}yr ago`
})

function difficultyVariant(key: string) {
  const map: Record<string, 'completed' | 'info' | 'warning' | 'failed'> = {
    very_easy: 'completed',
    easy: 'completed',
    moderate: 'warning',
    hard: 'warning',
    very_hard: 'failed',
  }
  return map[key] ?? 'info'
}

function healthVariant(key: string) {
  const map: Record<string, 'completed' | 'info' | 'warning' | 'failed'> = {
    thriving: 'completed',
    active: 'completed',
    stable: 'info',
    declining: 'warning',
    abandoned: 'failed',
  }
  return map[key] ?? 'info'
}

function complexityVariant(key: string) {
  const map: Record<string, 'completed' | 'info' | 'warning' | 'failed'> = {
    simple: 'completed',
    moderate: 'info',
    complex: 'warning',
    very_complex: 'failed',
  }
  return map[key] ?? 'info'
}

function docVariant(key: string) {
  const map: Record<string, 'completed' | 'info' | 'warning' | 'failed'> = {
    excellent: 'completed',
    good: 'completed',
    fair: 'warning',
    poor: 'warning',
    missing: 'failed',
  }
  return map[key] ?? 'info'
}

function formatStat(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

function tagLabel(tag: string): string {
  return tag.replace(/-/g, ' ').replace('license:', 'License: ')
}

function tagVariant(tag: string): string {
  if (tag === 'archived' || tag === 'abandoned' || tag === 'security-concerns') return 'failed'
  if (tag === 'actively-maintained' || tag === 'well-tested' || tag === 'clean-secrets' || tag === 'well-documented') return 'completed'
  if (tag === 'no-ci' || tag === 'sparse-docs' || tag === 'highly-complex') return 'warning'
  return 'info'
}

const langBarColors = [
  '#0969da', '#2da44e', '#e36209', '#8250df', '#0550ae',
  '#953800', '#1a7f37', '#6639ba', '#c0392b', '#16a085',
]

function langColor(idx: number): string {
  return langBarColors[idx % langBarColors.length]
}

const communityFiles = computed(() => [
  { key: 'readme', label: 'README', present: readme?.found ?? false, icon: '📄' },
  {
    key: 'license',
    label: structure?.license_type ? `License (${structure.license_type})` : 'License',
    present: !!structure?.license_file,
    icon: '⚖️',
  },
  { key: 'contributing', label: 'Contributing Guide', present: !!structure?.has_contributing, icon: '🤝' },
  { key: 'changelog', label: 'Changelog', present: !!structure?.has_changelog, icon: '📋' },
  { key: 'coc', label: 'Code of Conduct', present: !!structure?.has_coc, icon: '🌐' },
  { key: 'security', label: 'Security Policy', present: !!structure?.has_security_policy, icon: '🔒' },
])
</script>

<template>
  <div class="panel project-panel">

    <!-- About -->
    <section v-if="description || gh?.homepage" class="project-panel__section">
      <h2 class="panel__title">About</h2>
      <AppCard>
        <p v-if="description" class="project-panel__description">{{ description }}</p>
        <a
          v-if="gh?.homepage"
          :href="gh.homepage"
          target="_blank"
          rel="noopener noreferrer"
          class="project-panel__homepage"
        >
          🔗 {{ gh.homepage }}
        </a>
      </AppCard>
    </section>

    <!-- Classifications -->
    <section v-if="cls" class="project-panel__section">
      <h2 class="panel__title">Repository Assessment</h2>

      <div class="classify-grid">
        <AppCard>
          <div class="classify-card">
            <div class="classify-card__icon">🚀</div>
            <div class="classify-card__body">
              <div class="classify-card__heading">Contribution Difficulty</div>
              <AppBadge :variant="difficultyVariant(cls.contribution_difficulty.key)">
                {{ cls.contribution_difficulty.label }}
              </AppBadge>
            </div>
          </div>
        </AppCard>
        <AppCard>
          <div class="classify-card">
            <div class="classify-card__icon">❤️</div>
            <div class="classify-card__body">
              <div class="classify-card__heading">Project Health</div>
              <AppBadge :variant="healthVariant(cls.project_health.key)">
                {{ cls.project_health.label }}
              </AppBadge>
            </div>
          </div>
        </AppCard>
        <AppCard>
          <div class="classify-card">
            <div class="classify-card__icon">🧩</div>
            <div class="classify-card__body">
              <div class="classify-card__heading">Code Complexity</div>
              <AppBadge :variant="complexityVariant(cls.code_complexity.key)">
                {{ cls.code_complexity.label }}
              </AppBadge>
            </div>
          </div>
        </AppCard>
        <AppCard>
          <div class="classify-card">
            <div class="classify-card__icon">📚</div>
            <div class="classify-card__body">
              <div class="classify-card__heading">Documentation</div>
              <AppBadge :variant="docVariant(cls.documentation_grade.key)">
                {{ cls.documentation_grade.label }}
              </AppBadge>
            </div>
          </div>
        </AppCard>
      </div>

      <!-- Tags -->
      <div v-if="cls.tags.length" class="project-panel__tags">
        <AppBadge
          v-for="tag in cls.tags"
          :key="tag"
          :variant="(tagVariant(tag) as any)"
          class="project-panel__tag"
        >
          {{ tagLabel(tag) }}
        </AppBadge>
      </div>
    </section>

    <!-- GitHub Stats -->
    <section v-if="gh && (gh.stars || gh.forks || gh.open_issues)" class="project-panel__section">
      <h2 class="panel__title">GitHub Stats</h2>
      <div class="panel__grid">
        <AppCard>
          <div class="stat">
            <div class="stat__value">{{ formatStat(gh.stars) }}</div>
            <div class="stat__label">★ Stars</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="stat">
            <div class="stat__value">{{ formatStat(gh.forks) }}</div>
            <div class="stat__label">⑂ Forks</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="stat">
            <div class="stat__value">{{ formatStat(gh.open_issues) }}</div>
            <div class="stat__label">⚠ Open Issues</div>
          </div>
        </AppCard>
        <AppCard v-if="gh.open_prs !== null">
          <div class="stat">
            <div class="stat__value">{{ gh.open_prs }}</div>
            <div class="stat__label">⊞ Open PRs</div>
          </div>
        </AppCard>
        <AppCard v-if="gh.watchers">
          <div class="stat">
            <div class="stat__value">{{ formatStat(gh.watchers) }}</div>
            <div class="stat__label">👁 Watchers</div>
          </div>
        </AppCard>
      </div>

      <!-- Topics -->
      <div v-if="gh.topics?.length" class="project-panel__tags" style="margin-top:1rem">
        <AppBadge
          v-for="topic in gh.topics"
          :key="topic"
          variant="info"
          class="project-panel__tag"
        >
          {{ topic }}
        </AppBadge>
      </div>
    </section>

    <!-- Languages -->
    <section v-if="structure?.languages?.length" class="project-panel__section">
      <h2 class="panel__title">Languages</h2>
      <AppCard>
        <div class="lang-list">
          <div
            v-for="(lang, idx) in structure.languages.slice(0, 10)"
            :key="lang.name"
            class="lang-item"
          >
            <div class="lang-item__meta">
              <span class="lang-item__dot" :style="{ background: langColor(idx) }" />
              <span class="lang-item__name">{{ lang.name }}</span>
              <span class="lang-item__pct">{{ lang.pct }}%</span>
              <span class="lang-item__files">{{ lang.files.toLocaleString() }} files</span>
            </div>
            <div class="lang-bar">
              <div
                class="lang-bar__fill"
                :style="{ width: `${lang.pct}%`, background: langColor(idx) }"
              />
            </div>
          </div>
        </div>
      </AppCard>
    </section>

    <!-- Community Health -->
    <section class="project-panel__section">
      <h2 class="panel__title">Community Health Files</h2>
      <AppCard>
        <div class="health-grid">
          <div
            v-for="item in communityFiles"
            :key="item.label"
            :class="[
              'health-item',
              item.present ? 'health-item--present' : 'health-item--missing',
              item.present && item.key && fileContent(item.key) ? 'health-item--clickable' : '',
            ]"
            @click="item.present && item.key && fileContent(item.key) ? toggleFile(item.key) : undefined"
          >
            <span class="health-item__check">{{ item.present ? '✓' : '✗' }}</span>
            <span class="health-item__icon">{{ item.icon }}</span>
            <span class="health-item__label">{{ item.label }}</span>
            <span
              v-if="item.present && item.key && fileContent(item.key)"
              class="health-item__expand"
            >
              {{ expandedFile === item.key ? '▲' : '▼' }}
            </span>
          </div>
        </div>

        <!-- File content viewers -->
        <template v-for="item in communityFiles" :key="`content-${item.label}`">
          <div
            v-if="item.key && expandedFile === item.key && fileContent(item.key)"
            class="file-viewer"
          >
            <div class="file-viewer__header">
              {{ item.icon }} {{ item.label }}
              <button class="file-viewer__close" @click="expandedFile = null">✕</button>
            </div>
            <div
              v-if="isMarkdown(item.key)"
              class="file-viewer__markdown"
              v-html="renderMarkdown(fileContent(item.key)!)"
            />
            <pre v-else class="file-viewer__content">{{ fileContent(item.key) }}</pre>
          </div>
        </template>
      </AppCard>
    </section>

    <!-- Project Metadata -->
    <section v-if="structure" class="project-panel__section">
      <h2 class="panel__title">Project Info</h2>
      <div class="panel__grid">
        <AppCard v-if="repoAge">
          <div class="stat">
            <div class="stat__value stat__value--md">{{ repoAge }}</div>
            <div class="stat__label">Repository Age</div>
          </div>
        </AppCard>
        <AppCard class="release-card">
          <template v-if="gh?.releases_meta">
            <div class="release-card__stats">
              <div class="release-card__col">
                <div class="stat__value stat__value--md">{{ gh.releases_meta.stable_count }}</div>
                <div class="stat__label">Releases</div>
              </div>
              <div class="release-card__divider" />
              <div class="release-card__col">
                <div class="stat__value stat__value--md">{{ gh.releases_meta.prerelease_count }}</div>
                <div class="stat__label">Pre-releases</div>
              </div>
              <div class="release-card__divider" />
              <div class="release-card__col">
                <div class="stat__value stat__value--md">{{ gh.releases_meta.total_count }}</div>
                <div class="stat__label">Total</div>
              </div>
            </div>
            <div v-if="gh.releases_meta.latest_stable" class="release-card__latest">
              Latest: <strong>{{ gh.releases_meta.latest_stable.name }}</strong>
              <template v-if="lastReleaseAge"> · {{ lastReleaseAge }}</template>
            </div>
          </template>
          <template v-else>
            <div class="stat">
              <div class="stat__value stat__value--md">{{ structure.release_count }}</div>
              <div class="stat__label">
                Releases
                <span v-if="structure.last_release" class="stat__sub">
                  (latest: {{ structure.last_release.name }}<template v-if="lastReleaseAge">, {{ lastReleaseAge }}</template>)
                </span>
              </div>
            </div>
          </template>
        </AppCard>
        <AppCard>
          <div class="stat">
            <div class="stat__value stat__value--md">{{ structure.total_files.toLocaleString() }}</div>
            <div class="stat__label">Files ({{ structure.total_lines.toLocaleString() }} lines)</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="stat">
            <div class="stat__value stat__value--md">{{ structure.bus_factor }}</div>
            <div class="stat__label">Bus Factor</div>
          </div>
        </AppCard>
      </div>

      <!-- CI & tooling row -->
      <div class="ci-row" style="margin-top:1rem">
        <AppBadge v-if="structure.has_ci" variant="completed">
          CI: {{ structure.ci_systems.join(', ') }}
        </AppBadge>
        <AppBadge v-else variant="failed">No CI detected</AppBadge>

        <AppBadge v-if="structure.has_lint_config" variant="completed">Linting</AppBadge>
        <AppBadge v-else variant="warning">No Lint Config</AppBadge>

        <AppBadge v-if="structure.has_docker" variant="info">Docker</AppBadge>

        <AppBadge variant="info">
          Tests: {{ (structure.test_ratio * 100).toFixed(0) }}% ratio
        </AppBadge>
      </div>
    </section>

    <!-- GitHub Contributors -->
    <section v-if="gh?.contributors?.length" class="project-panel__section">
      <h2 class="panel__title">GitHub Contributors <span class="panel__title-sub">(top 30 by commits)</span></h2>
      <AppCard>
        <div class="contributor-grid">
          <a
            v-for="contrib in gh.contributors"
            :key="contrib.login"
            :href="contrib.html_url"
            target="_blank"
            rel="noopener noreferrer"
            class="contributor-card"
            :title="`${contrib.login} — ${contrib.contributions} commits`"
          >
            <img
              :src="contrib.avatar_url + '&s=64'"
              :alt="contrib.login"
              class="contributor-card__avatar"
              loading="lazy"
            />
            <span class="contributor-card__login">{{ contrib.login }}</span>
            <span class="contributor-card__count">{{ contrib.contributions.toLocaleString() }}</span>
          </a>
        </div>
      </AppCard>
    </section>

    <!-- Hot Files -->
    <section v-if="structure?.hot_files?.length" class="project-panel__section">
      <h2 class="panel__title">Hot Files <span class="panel__title-sub">(most changed, last 300 commits)</span></h2>
      <AppCard>
        <input
          v-model="hotFilesFilter.query.value"
          class="table-search"
          placeholder="Search files…"
        />
        <table class="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th class="runs-table__sortable" @click="hotFilesFilter.setSort('file')">
                File {{ hotFilesFilter.sortIcon('file') }}
              </th>
              <th class="runs-table__sortable" @click="hotFilesFilter.setSort('commit_count')">
                Times Changed {{ hotFilesFilter.sortIcon('commit_count') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(hf, idx) in (hotFilesFilter.filtered.value as any[])" :key="hf.file">
              <td>{{ idx + 1 }}</td>
              <td>{{ hf.file }}</td>
              <td>{{ hf.commit_count.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </AppCard>
    </section>

    <!-- Security Issues -->
    <section v-if="security?.issues?.length" class="project-panel__section">
      <h2 class="panel__title">Security Concerns</h2>
      <AppCard>
        <div
          v-for="issue in security.issues"
          :key="issue.detail"
          class="security-issue"
          :class="`security-issue--${issue.severity}`"
        >
          <AppBadge
            :variant="issue.severity === 'high' ? 'failed' : issue.severity === 'medium' ? 'warning' : 'info'"
          >
            {{ issue.severity }}
          </AppBadge>
          <span class="security-issue__detail">{{ issue.detail }}</span>
        </div>
      </AppCard>
    </section>
  </div>
</template>
