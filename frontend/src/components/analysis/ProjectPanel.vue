<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{ result: RunResult }>()

const { readme, structure, github_meta: gh, classification: cls } = props.result

interface DisplayLink {
  label: string
  url: string
  description: string
  badge: string
}

// Community file modal
const expandedFile = ref<string | null>(null)

function toggleFile(key: string) {
  expandedFile.value = key
}

function closeModal() {
  expandedFile.value = null
}

function onModalKey(e: KeyboardEvent) {
  if (e.key === 'Escape') closeModal()
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

function isDocsLikeUrl(url: string): boolean {
  const low = url.toLowerCase()
  return low.includes('docs.') || low.includes('/docs') || low.includes('/documentation') || low.includes('/wiki') || low.includes('readthedocs') || low.includes('confluence.') || low.includes('notion.so')
}

function pushUniqueLink(target: DisplayLink[], link: DisplayLink): void {
  if (target.some((it) => it.url === link.url)) return
  target.push(link)
}

function hostLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

const docsLinks = computed<DisplayLink[]>(() => {
  const links: DisplayLink[] = []

  for (const link of readme?.docs_links ?? []) {
    pushUniqueLink(links, {
      label: link.label || hostLabel(link.url),
      url: link.url,
      description: link.description || 'Documentation reference found in README',
      badge: 'Docs',
    })
  }

  if (gh?.homepage && isDocsLikeUrl(gh.homepage)) {
    pushUniqueLink(links, {
      label: 'Project Docs',
      url: gh.homepage,
      description: 'Repository homepage appears to be documentation',
      badge: 'Homepage',
    })
  }

  if (gh?.has_wiki && gh?.html_url) {
    pushUniqueLink(links, {
      label: 'GitHub Wiki',
      url: `${gh.html_url}/wiki`,
      description: 'Built-in wiki pages for setup and guides',
      badge: 'Wiki',
    })
  }

  if (structure?.docs_dir && gh?.html_url) {
    const folderLabel = structure.docs_dir.split('/').pop() ?? structure.docs_dir
    pushUniqueLink(links, {
      label: `/${structure.docs_dir}`,
      url: `${gh.html_url}/tree/${gh.default_branch ?? 'main'}/${structure.docs_dir}`,
      description: `Documentation folder found in repository root — browse the \`${folderLabel}\` directory`,
      badge: 'Docs Folder',
    })
  }

  return links
})

const interactionLinks = computed<DisplayLink[]>(() => {
  const links: DisplayLink[] = []

  for (const link of readme?.social_links ?? []) {
    pushUniqueLink(links, {
      label: link.label || link.platform || hostLabel(link.url),
      url: link.url,
      description: link.description || 'Community channel found in README',
      badge: link.platform || 'Social',
    })
  }

  if (gh?.html_url) {
    pushUniqueLink(links, {
      label: 'Issues',
      url: `${gh.html_url}/issues`,
      description: 'Report bugs and request features',
      badge: 'GitHub',
    })
    pushUniqueLink(links, {
      label: 'Pull Requests',
      url: `${gh.html_url}/pulls`,
      description: 'Review active contribution work',
      badge: 'GitHub',
    })
    if (gh.has_discussions) {
      pushUniqueLink(links, {
        label: 'Discussions',
        url: `${gh.html_url}/discussions`,
        description: 'Ask questions and discuss ideas',
        badge: 'Forum',
      })
    }
  }

  if (gh?.homepage && !isDocsLikeUrl(gh.homepage)) {
    pushUniqueLink(links, {
      label: 'Project Website',
      url: gh.homepage,
      description: 'Official project website',
      badge: 'Website',
    })
  }

  return links
})
</script>

<template>
  <div class="panel project-panel">

    <!-- Project Info — full width top row -->
    <section v-if="structure" class="project-panel__section project-panel__section--top">
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
      </div>
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

    <div class="project-panel__split">

      <!-- ── Left column: content sections ── -->
      <div class="project-panel__col">

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

        <!-- Documentation -->
        <section class="project-panel__section">
          <h2 class="panel__title">Documentation</h2>
          <AppCard>
            <div v-if="docsLinks.length" class="project-links">
              <a
                v-for="link in docsLinks"
                :key="link.url"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="project-links__item"
              >
                <div class="project-links__top">
                  <AppBadge variant="info">{{ link.badge }}</AppBadge>
                  <span class="project-links__label">{{ link.label }}</span>
                </div>
                <div class="project-links__desc">{{ link.description }}</div>
                <div class="project-links__url">{{ link.url }}</div>
              </a>
            </div>
            <div v-else class="project-empty">
              <AppBadge variant="failed">Not Found</AppBadge>
              <p class="project-empty__text">No documentation links were detected in repository metadata or README.</p>
            </div>
          </AppCard>
        </section>

        <!-- How to Interact -->
        <section class="project-panel__section">
          <h2 class="panel__title">How To Interact</h2>
          <AppCard>
            <div v-if="interactionLinks.length" class="project-links">
              <a
                v-for="link in interactionLinks"
                :key="link.url"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="project-links__item"
              >
                <div class="project-links__top">
                  <AppBadge variant="completed">{{ link.badge }}</AppBadge>
                  <span class="project-links__label">{{ link.label }}</span>
                </div>
                <div class="project-links__desc">{{ link.description }}</div>
                <div class="project-links__url">{{ link.url }}</div>
              </a>
            </div>
            <div v-else class="project-empty">
              <AppBadge variant="warning">Not Found</AppBadge>
              <p class="project-empty__text">No social or community links were detected from this repository.</p>
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
                <span v-if="item.present && item.key && fileContent(item.key)" class="health-item__expand">↗</span>
              </div>
            </div>
          </AppCard>
        </section>

      </div>

      <!-- ── Right column: data / metric sections ── -->
      <div class="project-panel__col">

        <!-- Repository Assessment -->
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
                  <span v-if="lang.files != null" class="lang-item__files">{{ lang.files.toLocaleString() }} files</span>
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


      </div>
    </div>
  </div>

  <!-- Community file modal -->
  <Teleport to="body">
    <Transition name="file-modal">
      <div v-if="expandedFile && fileContent(expandedFile)" class="file-modal" @keydown="onModalKey" @click.self="closeModal">
        <div class="file-modal__panel" role="dialog" aria-modal="true">
          <div class="file-modal__header">
            <span class="file-modal__title">
              {{ communityFiles.find(f => f.key === expandedFile)?.icon }}
              {{ communityFiles.find(f => f.key === expandedFile)?.label }}
            </span>
            <button class="file-modal__close" @click="closeModal" aria-label="Close">✕</button>
          </div>
          <div class="file-modal__body">
            <div
              v-if="isMarkdown(expandedFile)"
              class="file-viewer__markdown"
              v-html="renderMarkdown(fileContent(expandedFile)!)"
            />
            <pre v-else class="file-viewer__content">{{ fileContent(expandedFile) }}</pre>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
