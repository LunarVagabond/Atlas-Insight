<script setup lang="ts">
import { computed, ref } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import ConstellationPanel from './ConstellationPanel.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{ result: RunResult; runId?: string }>()

const { commits, heuristics, structure, classification: cls } = props.result

const overallScore = Math.round(
  heuristics.reduce((acc, h) => acc + h.score, 0) / (heuristics.length || 1)
)

function scoreVariant(score: number): 'completed' | 'warning' | 'failed' {
  if (score < 30) return 'completed'
  if (score < 60) return 'warning'
  return 'failed'
}

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

  const vulns = r.security?.vulnerabilities ?? []
  const confirmedVulns = vulns.filter(v => !v.version_is_range)
  const rangeVulns = vulns.filter(v => v.version_is_range)
  if (confirmedVulns.length > 0) {
    findings.push({ icon: '🔒', text: `${confirmedVulns.length} known CVE${confirmedVulns.length > 1 ? 's' : ''} in dependencies`, variant: 'critical' })
  }
  if (rangeVulns.length > 0) {
    findings.push({ icon: '⚠️', text: `${rangeVulns.length} possible CVE${rangeVulns.length > 1 ? 's' : ''} — verify installed versions`, variant: 'warning' })
  }

  const secIssues = r.security?.issue_count ?? 0
  if (secIssues > 0) {
    findings.push({ icon: '⚠️', text: `${secIssues} security hygiene issue${secIssues > 1 ? 's' : ''} detected`, variant: 'warning' })
  }

  const totalContributors = r.commits.total_contributors ?? 0
  const busFactor = r.ownership?.bus_factor ?? r.structure?.bus_factor ?? 0
  if (busFactor > 0 && busFactor <= 2 && totalContributors > 1) {
    findings.push({ icon: '🚌', text: `Bus factor ${busFactor} — only ${busFactor === 1 ? '1 contributor' : '2 contributors'} own the majority of files`, variant: 'warning' })
  }

  const highRisk = heuristics.filter(h => h.score >= 70)
  for (const h of highRisk.slice(0, 2)) {
    findings.push({ icon: '📊', text: h.description, variant: 'warning' })
  }

  const godModules = r.graph?.god_modules?.length ?? 0
  if (godModules > 0) {
    findings.push({ icon: '🕸️', text: `${godModules} core file${godModules > 1 ? 's' : ''} — imported by many others, changing them ripples wide (see Core Files in Architecture tab)`, variant: 'info' })
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
    <!-- Key metrics -->
    <div class="panel__grid panel__grid--2col">
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
          <div class="stat__label">Overall Risk Score</div>
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
        <span class="overview-sparkline__label">
          {{ sparklineTooltip ?? 'Commit activity — last 12 months' }}
        </span>
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
      <div class="overview-sparkline__axis">
        <span>{{ formatMonth(sparklineMonths[0].month) }}</span>
        <span>{{ formatMonth(sparklineMonths[sparklineMonths.length - 1].month) }}</span>
      </div>
    </div>

    <!-- Notable findings (only when parent hasn't taken over rendering) -->
    <div v-if="notableFindings.length" class="overview-findings">
      <h3 class="overview-findings__title">What Stands Out</h3>
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

    <!-- Constellation: related repos -->
    <ConstellationPanel v-if="runId" :run-id="runId" />

    <!-- Sub-project scorecards -->
    <div v-if="result.repo_type?.sub_projects?.length" class="overview-subprojects">
      <h3 class="overview-subprojects__title">Sub-projects</h3>
      <div class="overview-subprojects__grid">
        <AppCard
          v-for="sp in result.repo_type.sub_projects"
          :key="sp.name"
          class="overview-subprojects__card"
        >
          <div class="overview-subprojects__name">{{ sp.name }}</div>
          <div class="overview-subprojects__langs">
            <AppBadge v-for="lang in sp.languages.slice(0, 2)" :key="lang" variant="info">{{ lang }}</AppBadge>
          </div>
          <div v-if="sp.oss_score" class="overview-subprojects__score">
            <span
              class="overview-subprojects__score-val"
              :class="`overview-subprojects__score-val--${sp.oss_score.score >= 7 ? 'good' : sp.oss_score.score >= 4 ? 'mid' : 'low'}`"
            >{{ sp.oss_score.score.toFixed(1) }}</span>
            <span class="overview-subprojects__score-label">{{ sp.oss_score.label }}</span>
          </div>
          <div class="overview-subprojects__deps">
            {{ sp.dependencies.dependency_count }} deps
            <span v-if="sp.security.issue_count" class="overview-subprojects__issues">
              · {{ sp.security.issue_count }} issue{{ sp.security.issue_count === 1 ? '' : 's' }}
            </span>
          </div>
        </AppCard>
      </div>
    </div>
  </div>
</template>
