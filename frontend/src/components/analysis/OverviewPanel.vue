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

// ── Archetype (C) ─────────────────────────────────────────────────────────────
interface Archetype {
  icon: string
  label: string
  description: string
}

const repoArchetype = computed<Archetype | null>(() => {
  const r = props.result
  const cls = r.classification
  if (!cls) return null

  const health = cls.project_health.key
  const difficulty = cls.contribution_difficulty.key
  const complexity = cls.code_complexity.key
  const docs = cls.documentation_grade.key
  const tags = cls.tags ?? []

  const has = (t: string) => tags.includes(t)
  const thriving = health === 'thriving' || health === 'active'
  const dormant = health === 'abandoned' || health === 'declining'

  if (has('archived') || health === 'abandoned') {
    return { icon: '💀', label: 'Legacy Codebase', description: 'Inactive or archived — minimal to no ongoing development' }
  }
  if (thriving && (has('wildly-popular') || has('popular'))) {
    return { icon: '🚀', label: 'Rocket Ship', description: 'Thriving project with high community traction and active development' }
  }
  if (thriving && (has('large-community') || has('thriving-community'))) {
    return { icon: '⚡', label: 'Community Powerhouse', description: 'Large active contributor base driving rapid development' }
  }
  if ((docs === 'excellent' || docs === 'good') && (complexity === 'simple' || complexity === 'moderate')) {
    return { icon: '📚', label: 'Well-documented Library', description: 'Clean codebase with strong documentation — easy to learn from' }
  }
  if ((difficulty === 'very_easy' || difficulty === 'easy') && has('welcoming')) {
    return { icon: '🤝', label: 'Contributor-friendly', description: 'Low barrier to entry with good onboarding for new contributors' }
  }
  if (thriving && (complexity === 'very_complex' || complexity === 'complex')) {
    return { icon: '🏗️', label: 'Complex Machine', description: 'Actively developed but architecturally dense — steep learning curve' }
  }
  if (thriving && (complexity === 'simple' || complexity === 'moderate')) {
    return { icon: '🌱', label: 'Growing Project', description: 'Active development with manageable complexity — good momentum' }
  }
  if (health === 'stable') {
    return { icon: '🏛️', label: 'Mature & Stable', description: 'Established project with steady maintenance and low churn' }
  }
  if (dormant) {
    return { icon: '📉', label: 'Winding Down', description: 'Declining activity — may still be useful but development is slowing' }
  }
  return { icon: '🔍', label: 'Under the Radar', description: 'Early-stage or niche project — small but potentially useful' }
})

// ── Notable Findings (A) ──────────────────────────────────────────────────────
interface Finding {
  icon: string
  text: string
  variant: 'critical' | 'warning' | 'info' | 'success'
}

const notableFindings = computed<Finding[]>(() => {
  const findings: Finding[] = []
  const r = props.result

  if (r.github_meta?.archived) {
    findings.push({ icon: '📦', text: 'Repository is archived — no longer accepting contributions', variant: 'critical' })
  }

  if (r.commits.abandoned) {
    findings.push({ icon: '💤', text: `No commits in over a year (${r.commits.days_since_last_commit} days silent)`, variant: 'critical' })
  }

  const vulnCount = r.security?.vulnerabilities?.length ?? 0
  if (vulnCount > 0) {
    findings.push({ icon: '🔒', text: `${vulnCount} known CVE${vulnCount > 1 ? 's' : ''} in dependencies`, variant: 'critical' })
  }

  const secIssues = r.security?.issue_count ?? 0
  if (secIssues > 0) {
    findings.push({ icon: '⚠️', text: `${secIssues} security hygiene issue${secIssues > 1 ? 's' : ''} detected`, variant: 'warning' })
  }

  const busFactor = r.ownership?.bus_factor ?? r.structure?.bus_factor ?? 0
  if (busFactor > 0 && busFactor <= 2) {
    findings.push({ icon: '🚌', text: `Bus factor ${busFactor} — only ${busFactor === 1 ? '1 contributor' : '2 contributors'} own the majority of files`, variant: 'warning' })
  }

  const highRisk = heuristics.filter(h => h.score >= 70)
  for (const h of highRisk.slice(0, 2)) {
    findings.push({ icon: '📊', text: h.description, variant: 'warning' })
  }

  const godModules = r.graph?.god_modules?.length ?? 0
  if (godModules > 0) {
    findings.push({ icon: '🕸️', text: `${godModules} god module${godModules > 1 ? 's' : ''} — highly coupled files that many things depend on`, variant: 'info' })
  }

  const beginnerIssues = (r.contribution_opportunities ?? []).filter(
    o => o.difficulty === 'beginner' && o.category === 'github-issue' && o.readiness_label === 'Ready'
  ).length
  if (beginnerIssues > 0) {
    findings.push({ icon: '✅', text: `${beginnerIssues} ready-to-pick beginner issue${beginnerIssues > 1 ? 's' : ''} — great entry points for new contributors`, variant: 'success' })
  }

  if (cls && ['very_easy', 'easy'].includes(cls.contribution_difficulty.key) && beginnerIssues === 0) {
    findings.push({ icon: '🟢', text: `Contribution difficulty rated "${cls.contribution_difficulty.label}" — welcoming codebase`, variant: 'success' })
  }

  return findings.slice(0, 6)
})

// ── Sparkline (D) ─────────────────────────────────────────────────────────────
const sparklineMonths = computed(() => {
  const monthly = commits.monthly_frequency ?? []
  const last12 = monthly.slice(-12)
  if (last12.length === 0) return []
  const max = Math.max(...last12.map(m => m.count), 1)
  return last12.map(m => ({
    month: m.month,
    count: m.count,
    pct: Math.round((m.count / max) * 100),
  }))
})

const sparklineTooltip = ref<string | null>(null)

function formatMonth(ym: string): string {
  const [y, mo] = ym.split('-')
  const d = new Date(Number(y), Number(mo) - 1, 1)
  return d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}
</script>

<template>
  <div class="panel">
    <div class="panel__title-row">
      <h2 class="panel__title">Overview</h2>
      <div v-if="repoArchetype" class="repo-archetype">
        <span class="repo-archetype__icon">{{ repoArchetype.icon }}</span>
        <span class="repo-archetype__label">{{ repoArchetype.label }}</span>
        <span class="repo-archetype__desc">{{ repoArchetype.description }}</span>
      </div>
    </div>

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

    <!-- Commit sparkline -->
    <div v-if="sparklineMonths.length" class="overview-sparkline">
      <div class="overview-sparkline__header">
        <span class="overview-sparkline__tooltip">{{ sparklineTooltip ?? ' ' }}</span>
        <span class="overview-sparkline__sub">{{ commits.days_since_last_commit != null ? `Last commit ${commits.days_since_last_commit}d ago` : '' }}</span>
      </div>
      <div class="overview-sparkline__bars">
        <div
          v-for="m in sparklineMonths"
          :key="m.month"
          class="overview-sparkline__col"
          @mouseenter="sparklineTooltip = `${formatMonth(m.month)}: ${m.count} commit${m.count !== 1 ? 's' : ''}`"
          @mouseleave="sparklineTooltip = null"
        >
          <div
            class="overview-sparkline__bar"
            :style="{ height: `${Math.max(m.pct, 4)}%` }"
            :class="m.count === 0 ? 'overview-sparkline__bar--empty' : ''"
          />
        </div>
      </div>
    </div>

    <!-- Notable findings -->
    <div v-if="notableFindings.length" class="overview-findings">
      <h3 class="overview-findings__title">What stood out</h3>
      <ul class="overview-findings__list">
        <li
          v-for="(f, i) in notableFindings"
          :key="i"
          :class="['overview-findings__item', `overview-findings__item--${f.variant}`]"
        >
          <span class="overview-findings__icon">{{ f.icon }}</span>
          <span class="overview-findings__text">{{ f.text }}</span>
        </li>
      </ul>
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
