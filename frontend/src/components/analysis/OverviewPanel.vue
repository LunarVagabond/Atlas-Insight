<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{ result: RunResult }>()

const { commits, heuristics, github_meta: gh, structure, classification: cls, readme } = props.result

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

interface QuickLink {
  label: string
  url: string
  variant: 'info' | 'completed'
}

function pushQuickLink(target: QuickLink[], link: QuickLink): void {
  if (target.some((it) => it.url === link.url)) return
  target.push(link)
}

const overviewInteractionLinks = computed<QuickLink[]>(() => {
  const links: QuickLink[] = []

  for (const link of readme?.social_links ?? []) {
    pushQuickLink(links, {
      label: link.platform || link.label,
      url: link.url,
      variant: 'completed',
    })
  }

  if (gh?.html_url) {
    pushQuickLink(links, { label: 'Issues', url: `${gh.html_url}/issues`, variant: 'info' })
    if (gh.has_discussions) {
      pushQuickLink(links, { label: 'Discussions', url: `${gh.html_url}/discussions`, variant: 'info' })
    }
    if (gh.has_wiki) {
      pushQuickLink(links, { label: 'Wiki', url: `${gh.html_url}/wiki`, variant: 'info' })
    }
  }

  return links.slice(0, 6)
})

interface CommunityTab {
  key: 'readme' | 'contributing' | 'license' | 'changelog' | 'coc' | 'security'
  label: string
  content: string | null
}

const selectedTab = ref<CommunityTab['key']>('readme')

const communityTabs = computed<CommunityTab[]>(() => [
  { key: 'readme', label: 'README', content: readme?.content ?? null },
  { key: 'contributing', label: 'Contributing', content: structure?.community_files_content?.contributing ?? null },
  { key: 'license', label: 'License', content: structure?.community_files_content?.license ?? null },
  { key: 'changelog', label: 'Changelog', content: structure?.community_files_content?.changelog ?? null },
  { key: 'coc', label: 'Code of Conduct', content: structure?.community_files_content?.coc ?? null },
  { key: 'security', label: 'Security Policy', content: structure?.community_files_content?.security ?? null },
])

const availableCommunityTabs = computed<CommunityTab[]>(() =>
  communityTabs.value.filter((tab) => !!tab.content?.trim())
)

const selectedTabData = computed(() => {
  const current = availableCommunityTabs.value.find((tab) => tab.key === selectedTab.value)
  return current ?? availableCommunityTabs.value[0]
})

function renderMarkdown(md: string): string {
  return marked.parse(md, { async: false }) as string
}

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
      <AppCard v-if="structure?.total_lines">
        <div class="stat">
          <div class="stat__value">{{ structure.total_lines.toLocaleString() }}</div>
          <div class="stat__label">Lines of Code</div>
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

    <!-- Topics -->
    <div v-if="gh?.topics?.length" class="overview-topics">
      <span v-for="topic in gh.topics" :key="topic" class="overview-topics__tag">{{ topic }}</span>
    </div>

    <div v-if="overviewInteractionLinks.length" class="overview-links">
      <a
        v-for="link in overviewInteractionLinks"
        :key="link.url"
        :href="link.url"
        target="_blank"
        rel="noopener noreferrer"
        class="overview-links__item"
      >
        <AppBadge :variant="link.variant">{{ link.label }}</AppBadge>
      </a>
    </div>

    <!-- Language bar + legend -->
    <div v-if="topLanguages.length" class="overview-langs">
      <div class="overview-langs__bar-row">
        <div
          v-for="(lang, idx) in topLanguages"
          :key="lang.name"
          class="overview-langs__segment"
          :style="{ width: `${lang.pct}%` }"
          :title="`${lang.name}: ${lang.pct}%`"
        >
          <div class="overview-langs__bar" :style="{ background: langBarColors[idx] }" />
        </div>
      </div>
      <div class="overview-langs__legend">
        <span v-for="(lang, idx) in topLanguages" :key="lang.name" class="overview-langs__legend-item">
          <span class="overview-langs__dot" :style="{ background: langBarColors[idx] }" />
          <span class="overview-langs__name">{{ lang.name }}</span>
          <span class="overview-langs__pct">{{ lang.pct }}%</span>
        </span>
      </div>
    </div>

    <div v-if="availableCommunityTabs.length" class="overview-readme">
      <h3 class="overview-readme__title">Community Files</h3>
      <AppCard>
        <div class="overview-readme__tabs">
          <button
            v-for="tab in availableCommunityTabs"
            :key="tab.key"
            type="button"
            :class="['overview-readme__tab', selectedTab === tab.key ? 'overview-readme__tab--active' : '']"
            @click="selectedTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div
          v-if="selectedTabData?.content"
          class="file-viewer__markdown overview-readme__content"
          v-html="renderMarkdown(selectedTabData.content.slice(0, 24_000))"
        />
      </AppCard>
    </div>
  </div>
</template>
