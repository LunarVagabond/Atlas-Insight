<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import type { AnalysisRun, RunResult } from '../stores/analysis'
import logoUrl from '../assets/logo.png'

const route = useRoute()
const runId = route.params.runId as string

const run = ref<AnalysisRun | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let previousTitle = ''

onMounted(async () => {
  document.documentElement.setAttribute('data-layout', 'print')
  previousTitle = document.title
  try {
    const { data } = await axios.get(`/api/v1/repositories/runs/${runId}`)
    run.value = data
    if (data?.repo_owner && data?.repo_name) {
      document.title = `${data.repo_owner}/${data.repo_name} — Atlas Insight`
    }
  } catch {
    error.value = 'Failed to load analysis data.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.documentElement.removeAttribute('data-layout')
  if (previousTitle) document.title = previousTitle
})

const result = computed<RunResult | null>(() => {
  const r = run.value?.result
  if (!r || r.error) return null
  return r
})

// ── Helpers ──
function scoreLevel(score: number): 'low' | 'medium' | 'high' {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

function scoreRiskLabel(score: number): string {
  if (score < 30) return 'Low concern'
  if (score < 60) return 'Worth watching'
  return 'Needs attention'
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatNum(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString()
}

function formatPct(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${Math.round(n * 100)}%`
}

// ── Computed data ──
const overallScore = computed(() => {
  if (!result.value?.heuristics?.length) return null
  return Math.round(
    result.value.heuristics.reduce((s, h) => s + h.score, 0) / result.value.heuristics.length
  )
})

const sortedSignals = computed(() =>
  result.value ? [...result.value.heuristics].sort((a, b) => b.score - a.score) : []
)

const langBarColors = ['#0969da', '#2da44e', '#e36209', '#8250df', '#bc4c00']
const topLangs = computed(() => result.value?.structure?.languages?.slice(0, 5) ?? [])

const securityIssues = computed(() => {
  const issues = result.value?.security?.issues ?? []
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  return [...issues].sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))
})

const vulns = computed(() => result.value?.security?.vulnerabilities ?? [])

const cveSeverityCounts = computed(() => {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const v of vulns.value) {
    const s = (v.severity ?? '').toLowerCase()
    if (s.includes('critical')) counts.critical++
    else if (s.includes('high') || s.match(/9\.\d|10\.0/)) counts.high++
    else if (s.includes('medium') || s.includes('moderate')) counts.medium++
    else counts.low++
  }
  return counts
})

function cveRowClass(severity: string | null): string {
  const s = (severity ?? '').toLowerCase()
  if (s.includes('critical')) return 'print-cve-row--critical'
  if (s.includes('high')) return 'print-cve-row--high'
  if (s.includes('medium') || s.includes('moderate')) return 'print-cve-row--medium'
  return ''
}

function cveBadgeClass(severity: string | null): string {
  const s = (severity ?? '').toLowerCase()
  if (s.includes('critical')) return 'print-badge--critical'
  if (s.includes('high')) return 'print-badge--high'
  if (s.includes('medium') || s.includes('moderate')) return 'print-badge--medium'
  return 'print-badge--low'
}

const prodDeps = computed(() =>
  (result.value?.dependencies?.dependencies ?? []).filter(d => !d.dev).slice(0, 40)
)

const devDeps = computed(() =>
  (result.value?.dependencies?.dependencies ?? []).filter(d => d.dev).slice(0, 20)
)

const godModules = computed(() => result.value?.graph?.god_modules?.slice(0, 15) ?? [])
const hotFiles = computed(() => result.value?.structure?.hot_files?.slice(0, 15) ?? [])
const opportunities = computed(() => (result.value?.contribution_opportunities ?? []).slice(0, 20))
const subProjects = computed(() => result.value?.repo_type?.sub_projects ?? [])
const codeQuality = computed(() => ({
  complexity: result.value?.complexity,
  deadCode: result.value?.dead_code,
  junkFiles: result.value?.junk_files,
  testCoverage: result.value?.test_coverage,
}))
const devOps = computed(() => ({
  cicd: result.value?.cicd,
  containers: result.value?.containers,
  changelog: result.value?.changelog,
}))

const difficultyColor: Record<string, string> = {
  beginner: '#2da44e',
  intermediate: '#d97706',
  advanced: '#dc2626',
}

// Dynamic section numbering — CVE section only appears if vulns exist
const hasVulns = computed(() => vulns.value.length > 0)
const sectionNums = computed(() => {
  let n = 1
  return {
    summary: String(n++).padStart(2, '0'),
    health: String(n++).padStart(2, '0'),
    security: String(n++).padStart(2, '0'),
    vulns: hasVulns.value ? String(n++).padStart(2, '0') : null,
    project: String(n++).padStart(2, '0'),
    deps: String(n++).padStart(2, '0'),
    arch: String(n++).padStart(2, '0'),
    codeQuality: String(n++).padStart(2, '0'),
    devops: String(n++).padStart(2, '0'),
    subprojects: subProjects.value.length ? String(n++).padStart(2, '0') : null,
    contributing: opportunities.value.length ? String(n++).padStart(2, '0') : null,
  }
})

// ── Actions ──
function triggerPrint() { window.print() }
function triggerClose() { window.close() }

function exportCvesCsv() {
  if (!vulns.value.length || !run.value) return
  const header = ['Package', 'Version', 'CVE ID', 'Severity', 'Ecosystem', 'Summary', 'URL']
  const rows = vulns.value.map(v => [
    v.name,
    v.version ?? '',
    v.vuln_id,
    v.severity ?? '',
    v.ecosystem ?? '',
    `"${(v.summary ?? '').replace(/"/g, '""')}"`,
    v.url ?? '',
  ])
  const csv = [header, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${run.value.repo_owner}-${run.value.repo_name}-cve-report.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="print-view">

    <!-- ── Controls (screen only) ── -->
    <div class="print-controls">
      <div class="print-controls__inner">
        <div class="print-controls__brand-block">
          <img :src="logoUrl" alt="" class="print-controls__logo" />
          <span class="print-controls__brand">Atlas <span>Insight</span></span>
        </div>
        <span class="print-controls__sep" />
        <span class="print-controls__label">Analysis Report</span>
        <div class="print-controls__actions">
          <button
            class="print-controls__btn print-controls__btn--danger"
            :disabled="!hasVulns"
            :title="hasVulns ? 'Export CVE findings as CSV' : 'No CVEs found'"
            @click="exportCvesCsv"
          >
            ↓ Export CVEs (CSV)
          </button>
          <button class="print-controls__btn print-controls__btn--primary" @click="triggerPrint">
            ⎙ Print / Save PDF
          </button>
          <span class="print-controls__hint">Turn off “Headers and footers” in the print dialog for a clean PDF.</span>
          <button class="print-controls__btn" @click="triggerClose">✕</button>
        </div>
      </div>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading" class="print-state">Loading analysis…</div>
    <div v-else-if="error || !result" class="print-state print-state--error">
      {{ error ?? 'Analysis data unavailable.' }}
    </div>

    <template v-else-if="result && run">

      <!-- ══ COVER ══ -->
      <section class="print-cover">
        <header class="print-cover__header">
          <div class="print-cover__brand-block">
            <img :src="logoUrl" alt="" class="print-cover__logo" />
            <span class="print-cover__wordmark">Atlas <span>Insight</span></span>
          </div>
          <p class="print-cover__report-type">Repository Analysis Report</p>
        </header>

        <h1 class="print-cover__repo">
          {{ run.repo_owner }} / {{ run.repo_name }}
          <span v-if="run.branch" class="print-cover__branch">@ {{ run.branch }}</span>
        </h1>
        <p class="print-cover__meta">
          Analyzed {{ formatDate(run.completed_at) }}
          <template v-if="result.github_meta?.primary_language">
            · {{ result.github_meta.primary_language }}
          </template>
        </p>

        <!-- Key stats summary row -->
        <div class="print-cover__summary-row">
          <div class="print-cover__summary-cell">
            <div class="print-cover__summary-val">{{ formatNum(result.commits.total_commits) }}</div>
            <div class="print-cover__summary-label">Total Commits</div>
          </div>
          <div class="print-cover__summary-cell">
            <div class="print-cover__summary-val">{{ result.commits.total_contributors }}</div>
            <div class="print-cover__summary-label">Contributors</div>
          </div>
          <div class="print-cover__summary-cell">
            <div
              :class="['print-cover__summary-val', overallScore !== null ? `print-stat__value--${scoreLevel(overallScore)}` : '']"
            >
              {{ overallScore ?? '—' }}<span v-if="overallScore !== null" style="font-size:0.55em;color:#aaa;font-weight:400">/100</span>
            </div>
            <div class="print-cover__summary-label">Composite Risk</div>
          </div>
          <div class="print-cover__summary-cell">
            <div :class="['print-cover__summary-val', hasVulns ? 'print-risk--high' : '']">
              {{ vulns.length }}
            </div>
            <div class="print-cover__summary-label">CVEs Found</div>
          </div>
        </div>

        <!-- Classification -->
        <div v-if="result.classification" class="print-cover__classify">
          <div class="print-cover__classify-item">
            <span class="print-cover__classify-key">Health</span>
            <span class="print-cover__classify-val">{{ result.classification.project_health.label }}</span>
          </div>
          <div class="print-cover__classify-item">
            <span class="print-cover__classify-key">Contribution</span>
            <span class="print-cover__classify-val">{{ result.classification.contribution_difficulty.label }}</span>
          </div>
          <div class="print-cover__classify-item">
            <span class="print-cover__classify-key">Complexity</span>
            <span class="print-cover__classify-val">{{ result.classification.code_complexity.label }}</span>
          </div>
          <div class="print-cover__classify-item">
            <span class="print-cover__classify-key">Documentation</span>
            <span class="print-cover__classify-val">{{ result.classification.documentation_grade.label }}</span>
          </div>
          <div v-if="result.github_meta?.license_spdx ?? result.github_meta?.license_name" class="print-cover__classify-item">
            <span class="print-cover__classify-key">License</span>
            <span class="print-cover__classify-val">{{ result.github_meta!.license_spdx ?? result.github_meta!.license_name }}</span>
          </div>
        </div>

        <div class="print-cover__meta">
          <div class="print-cover__meta-row">
            <span class="print-cover__meta-key">Analyzed</span>
            <span class="print-cover__meta-val">{{ formatDate(run.completed_at) }}</span>
          </div>
          <div v-if="result.github_meta?.primary_language" class="print-cover__meta-row">
            <span class="print-cover__meta-key">Primary Language</span>
            <span class="print-cover__meta-val">{{ result.github_meta.primary_language }}</span>
          </div>
          <div class="print-cover__meta-row">
            <span class="print-cover__meta-key">Run ID</span>
            <span class="print-cover__meta-val print-cover__run-id">{{ run.id }}</span>
          </div>
        </div>

        <div v-if="result.github_meta?.github_description" class="print-cover__desc">
          {{ result.github_meta.github_description }}
        </div>

        <div v-if="result.github_meta?.topics?.length" class="print-cover__topics">
          <span v-for="t in result.github_meta.topics" :key="t" class="print-cover__topic">{{ t }}</span>
        </div>

        <div v-if="topLangs.length" class="print-cover__langs">
          <div class="print-langs">
            <div class="print-langs__bar">
              <div
                v-for="(lang, i) in topLangs"
                :key="lang.name"
                class="print-langs__seg"
                :style="{ width: `${lang.pct}%`, background: langBarColors[i] ?? '#888' }"
              />
            </div>
            <div class="print-langs__legend">
              <span v-for="(lang, i) in topLangs" :key="lang.name" class="print-langs__item">
                <span class="print-langs__dot" :style="{ background: langBarColors[i] ?? '#888' }" />
                {{ lang.name }} {{ lang.pct }}%
              </span>
            </div>
          </div>
        </div>

        <div v-if="result.commits.abandoned" class="print-alert print-alert--warn" style="margin-top:1rem">
          Repository appears abandoned — no commits in 365+ days.
        </div>
      </section>

      <!-- ══ §01 EXECUTIVE SUMMARY ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.summary }}</span>
          <h2 class="print-section__title">Executive Summary</h2>
        </div>

        <div class="print-stat-grid">
          <div class="print-stat">
            <div class="print-stat__value">{{ formatNum(result.commits.total_commits) }}</div>
            <div class="print-stat__label">Total Commits</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ formatNum(result.commits.total_contributors) }}</div>
            <div class="print-stat__label">Contributors</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ result.commits.days_since_last_commit ?? '—' }}</div>
            <div class="print-stat__label">Days Since Commit</div>
          </div>
          <div v-if="result.structure?.total_lines" class="print-stat">
            <div class="print-stat__value">{{ formatNum(result.structure.total_lines) }}</div>
            <div class="print-stat__label">Lines of Code</div>
          </div>
          <div v-if="overallScore !== null" class="print-stat">
            <div :class="['print-stat__value', `print-stat__value--${scoreLevel(overallScore)}`]">
              {{ overallScore }}<span class="print-stat__unit">/100</span>
            </div>
            <div class="print-stat__label">Composite Risk</div>
          </div>
          <div v-if="result.structure?.test_ratio != null" class="print-stat">
            <div class="print-stat__value">{{ formatPct(result.structure.test_ratio) }}</div>
            <div class="print-stat__label">Test Coverage</div>
          </div>
          <div v-if="result.structure?.total_files" class="print-stat">
            <div class="print-stat__value">{{ formatNum(result.structure.total_files) }}</div>
            <div class="print-stat__label">Total Files</div>
          </div>
          <div v-if="result.dependencies?.dependency_count" class="print-stat">
            <div class="print-stat__value">{{ result.dependencies.dependency_count }}</div>
            <div class="print-stat__label">Dependencies</div>
          </div>
        </div>

        <!-- GitHub meta table -->
        <div v-if="result.github_meta" style="margin-bottom:1.25rem">
          <table class="print-table print-table--bordered print-table--compact">
            <tbody>
              <tr v-if="result.github_meta.stars">
                <td class="print-table__key">Stars</td><td>{{ formatNum(result.github_meta.stars) }}</td>
                <td class="print-table__key">Forks</td><td>{{ formatNum(result.github_meta.forks) }}</td>
                <td class="print-table__key">Watchers</td><td>{{ formatNum(result.github_meta.watchers) }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Open Issues</td><td>{{ formatNum(result.github_meta.open_issues) }}</td>
                <td class="print-table__key">Open PRs</td><td>{{ result.github_meta.open_prs ?? '—' }}</td>
                <td class="print-table__key">Default Branch</td><td>{{ result.github_meta.default_branch }}</td>
              </tr>
              <tr v-if="result.github_meta.created_at">
                <td class="print-table__key">Created</td><td>{{ formatDate(result.github_meta.created_at) }}</td>
                <td class="print-table__key">Last Push</td><td>{{ formatDate(result.github_meta.pushed_at) }}</td>
                <td class="print-table__key">Size</td><td>{{ result.github_meta.size_kb ? `${(result.github_meta.size_kb / 1024).toFixed(1)} MB` : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Classification -->
        <div v-if="result.classification" style="margin-bottom:1rem">
          <table class="print-table print-table--bordered print-table--compact">
            <thead>
              <tr>
                <th>Project Health</th>
                <th>Contribution Difficulty</th>
                <th>Code Complexity</th>
                <th>Documentation</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>{{ result.classification.project_health.label }}</strong></td>
                <td><strong>{{ result.classification.contribution_difficulty.label }}</strong></td>
                <td><strong>{{ result.classification.code_complexity.label }}</strong></td>
                <td><strong>{{ result.classification.documentation_grade.label }}</strong></td>
              </tr>
            </tbody>
          </table>
          <div v-if="result.classification.tags?.length" class="print-tags">
            <span v-for="tag in result.classification.tags" :key="tag" class="print-tag">{{ tag }}</span>
          </div>
        </div>
      </section>

      <!-- ══ §02 HEALTH SIGNALS ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.health }}</span>
          <h2 class="print-section__title">Health Signals</h2>
        </div>
        <p class="print-section__intro">
          Automated signals about project activity, health, and contributor patterns.
          Scores are 0–100; higher = greater risk or concern.
        </p>

        <div v-if="overallScore !== null" class="print-composite">
          Composite Risk Score:
          <strong :class="`print-risk--${scoreLevel(overallScore)}`">{{ overallScore }} / 100</strong>
          &mdash; {{ scoreRiskLabel(overallScore) }}
        </div>

        <table class="print-table print-table--bordered">
          <thead>
            <tr>
              <th>Signal</th>
              <th class="print-table__num-col">Score</th>
              <th class="print-table__bar-col">Bar</th>
              <th>Risk Level</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sortedSignals" :key="s.signal">
              <td><strong>{{ s.label }}</strong></td>
              <td class="print-table__num-col">
                <strong :class="`print-risk--${scoreLevel(s.score)}`">{{ s.score }}</strong>
              </td>
              <td class="print-table__bar-col">
                <div class="print-score-track">
                  <div
                    class="print-score-fill"
                    :class="`print-score-fill--${scoreLevel(s.score)}`"
                    :style="{ width: `${s.score}%` }"
                  />
                </div>
              </td>
              <td>{{ scoreRiskLabel(s.score) }}</td>
              <td class="print-table__muted">{{ s.confidence }}</td>
            </tr>
          </tbody>
        </table>

        <div class="print-signal-details">
          <div
            v-for="s in sortedSignals"
            :key="`desc-${s.signal}`"
            :class="['print-signal-detail', `print-signal-detail--${scoreLevel(s.score)}`]"
          >
            <strong>{{ s.label }}</strong>
            {{ s.description }}
            <ul v-if="s.items?.length" class="print-signal-items">
              <li v-for="item in s.items.slice(0, 4)" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ══ §03 SECURITY ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.security }}</span>
          <h2 class="print-section__title">Security</h2>
        </div>
        <p class="print-section__intro">
          Automated pattern matching only — not a full security audit. Consult a security professional for production systems.
        </p>

        <div v-if="result.security" style="margin-bottom:1.25rem">
          <table class="print-table print-table--bordered print-table--compact">
            <tbody>
              <tr>
                <td class="print-table__key">Security Score</td>
                <td>
                  <strong :class="`print-risk--${scoreLevel(result.security.score)}`">
                    {{ result.security.score }} / 100
                  </strong>
                </td>
                <td class="print-table__key">.gitignore</td>
                <td>{{ result.security.gitignore_exists ? '✓ Present' : '✗ Missing' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Security Policy</td>
                <td>{{ result.structure?.has_security_policy ? (result.structure.security_policy_file ?? '✓ Present') : '✗ Not found' }}</td>
                <td class="print-table__key">Gitignore Gaps</td>
                <td>{{ result.security.gitignore_gaps?.length ? result.security.gitignore_gaps.join(', ') : 'None detected' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="print-subsection">Code Pattern Scan</div>
        <template v-if="securityIssues.length">
          <table class="print-table print-table--bordered">
            <thead>
              <tr><th>Severity</th><th>Type</th><th>Detail</th></tr>
            </thead>
            <tbody>
              <tr v-for="(issue, i) in securityIssues" :key="i">
                <td><span :class="['print-badge', `print-badge--${issue.severity}`]">{{ issue.severity }}</span></td>
                <td>{{ issue.type }}</td>
                <td>{{ issue.detail }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <div v-else class="print-clear">No common security patterns detected.</div>

        <!-- CVE summary line in security section if vulns exist — full detail in §04 -->
        <template v-if="hasVulns">
          <div class="print-alert print-alert--error" style="margin-top:1rem">
            {{ vulns.length }} dependency vulnerability{{ vulns.length !== 1 ? 'ies' : 'y' }} found
            ({{ cveSeverityCounts.critical }} critical · {{ cveSeverityCounts.high }} high ·
            {{ cveSeverityCounts.medium }} medium · {{ cveSeverityCounts.low }} low).
            Full details in section {{ sectionNums.vulns }}.
          </div>
        </template>
        <div v-else class="print-clear">No known CVEs detected in scanned dependencies.</div>
      </section>

      <!-- ══ §04 VULNERABILITY REPORT (conditional) ══ -->
      <section v-if="hasVulns" class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.vulns }}</span>
          <h2 class="print-section__title">Vulnerability Report</h2>
        </div>
        <p class="print-section__intro">
          Dependency vulnerabilities from OSV.dev scan at analysis time.
          Results reflect version specs found in dependency files — pinned lockfile versions are more accurate.
        </p>

        <!-- Severity summary -->
        <div class="print-cve-summary">
          <div class="print-cve-summary__cell print-cve-summary__cell--critical">
            <div class="print-cve-summary__count">{{ cveSeverityCounts.critical }}</div>
            <div class="print-cve-summary__label">Critical</div>
          </div>
          <div class="print-cve-summary__cell print-cve-summary__cell--high">
            <div class="print-cve-summary__count">{{ cveSeverityCounts.high }}</div>
            <div class="print-cve-summary__label">High</div>
          </div>
          <div class="print-cve-summary__cell print-cve-summary__cell--medium">
            <div class="print-cve-summary__count">{{ cveSeverityCounts.medium }}</div>
            <div class="print-cve-summary__label">Medium</div>
          </div>
          <div class="print-cve-summary__cell print-cve-summary__cell--low">
            <div class="print-cve-summary__count">{{ cveSeverityCounts.low }}</div>
            <div class="print-cve-summary__label">Low / Unknown</div>
          </div>
        </div>

        <table class="print-table print-table--bordered">
          <thead>
            <tr>
              <th>Package</th>
              <th>Version</th>
              <th>CVE / Advisory</th>
              <th>Severity</th>
              <th>Ecosystem</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in vulns" :key="v.vuln_id + v.name" :class="cveRowClass(v.severity)">
              <td><strong>{{ v.name }}</strong></td>
              <td class="print-table__mono">{{ v.version }}</td>
              <td class="print-table__mono" style="white-space:nowrap">{{ v.vuln_id }}</td>
              <td><span :class="['print-badge', cveBadgeClass(v.severity)]">{{ v.severity ?? 'unknown' }}</span></td>
              <td class="print-table__muted">{{ v.ecosystem ?? '—' }}</td>
              <td style="font-size:0.75rem">{{ v.summary }}</td>
            </tr>
          </tbody>
        </table>

        <p class="print-section__intro" style="margin-top:0.5rem">
          Source: <span class="print-table__mono">osv.dev</span> ·
          Scan performed at analysis time · Always verify against current lockfile versions before remediating.
        </p>
      </section>

      <!-- ══ §PROJECT STRUCTURE ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.project }}</span>
          <h2 class="print-section__title">Project Structure</h2>
        </div>

        <div v-if="result.structure" class="print-two-col">
          <table class="print-table print-table--bordered print-table--compact">
            <tbody>
              <tr><td class="print-table__key">Total Files</td><td>{{ formatNum(result.structure.total_files) }}</td></tr>
              <tr><td class="print-table__key">Lines of Code</td><td>{{ formatNum(result.structure.total_lines) }}</td></tr>
              <tr><td class="print-table__key">Test Files</td><td>{{ formatNum(result.structure.test_files) }} ({{ formatPct(result.structure.test_ratio) }})</td></tr>
              <tr><td class="print-table__key">Repository Age</td><td>{{ result.structure.repo_age_days ? `${result.structure.repo_age_days.toLocaleString()} days` : '—' }}</td></tr>
              <tr><td class="print-table__key">Bus Factor</td><td>{{ result.structure.bus_factor }}</td></tr>
              <tr><td class="print-table__key">Releases</td><td>{{ result.structure.release_count }}</td></tr>
              <tr v-if="result.structure.last_release">
                <td class="print-table__key">Last Release</td>
                <td>{{ result.structure.last_release.name }} ({{ formatDate(result.structure.last_release.date) }})</td>
              </tr>
            </tbody>
          </table>

          <table class="print-table print-table--bordered print-table--compact">
            <tbody>
              <tr><td class="print-table__key">CI / CD</td><td>{{ result.structure.has_ci ? (result.structure.ci_systems?.join(', ') || 'Yes') : 'Not detected' }}</td></tr>
              <tr><td class="print-table__key">Docker</td><td>{{ result.structure.has_docker ? 'Present' : 'Not found' }}</td></tr>
              <tr><td class="print-table__key">Lint Config</td><td>{{ result.structure.has_lint_config ? 'Present' : 'Not found' }}</td></tr>
              <tr><td class="print-table__key">License</td><td>{{ result.structure.license_type ?? (result.structure.license_file ?? 'Not found') }}</td></tr>
              <tr><td class="print-table__key">Contributing Guide</td><td>{{ result.structure.has_contributing ? (result.structure.contributing_file ?? 'Present') : 'Not found' }}</td></tr>
              <tr><td class="print-table__key">Code of Conduct</td><td>{{ result.structure.has_coc ? (result.structure.coc_file ?? 'Present') : 'Not found' }}</td></tr>
              <tr><td class="print-table__key">Changelog</td><td>{{ result.structure.has_changelog ? (result.structure.changelog_file ?? 'Present') : 'Not found' }}</td></tr>
            </tbody>
          </table>
        </div>

        <div v-if="result.structure?.tech_stack?.length">
          <div class="print-subsection">Tech Stack</div>
          <div class="print-tags">
            <span v-for="t in result.structure.tech_stack" :key="t" class="print-tag">{{ t }}</span>
          </div>
        </div>

        <template v-if="result.structure?.top_contributors?.length">
          <div class="print-subsection">Top Contributors</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>#</th><th>Author</th><th>Files Touched</th></tr></thead>
            <tbody>
              <tr v-for="(c, i) in result.structure.top_contributors.slice(0, 10)" :key="c.author">
                <td class="print-table__muted">{{ i + 1 }}</td>
                <td>{{ c.author }}</td>
                <td>{{ formatNum(c.files_touched) }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-if="(result.structure?.stale_branches?.length ?? 0) > 0">
          <div class="print-subsection">Stale Branches ({{ result.structure!.stale_branch_count }})</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>Branch</th><th>Last Commit</th><th>Days Stale</th></tr></thead>
            <tbody>
              <tr v-for="b in result.structure!.stale_branches!.slice(0, 10)" :key="b.name">
                <td class="print-table__mono">{{ b.name }}</td>
                <td>{{ formatDate(b.last_commit) }}</td>
                <td>{{ b.days_ago }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ══ §DEPENDENCIES ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.deps }}</span>
          <h2 class="print-section__title">Dependencies</h2>
        </div>

        <div class="print-stat-grid print-stat-grid--sm">
          <div class="print-stat">
            <div class="print-stat__value">{{ result.dependencies?.dependency_count ?? 0 }}</div>
            <div class="print-stat__label">Total</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ prodDeps.length }}</div>
            <div class="print-stat__label">Production</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ devDeps.length }}</div>
            <div class="print-stat__label">Dev</div>
          </div>
          <div class="print-stat">
            <div :class="['print-stat__value', hasVulns ? 'print-risk--high' : '']">{{ vulns.length }}</div>
            <div class="print-stat__label">CVEs</div>
          </div>
        </div>

        <div v-if="result.dependencies?.missing_lockfile_warnings?.length" class="print-alert print-alert--warn">
          Missing lockfile{{ result.dependencies.missing_lockfile_warnings.length > 1 ? 's' : '' }}:
          {{ result.dependencies.missing_lockfile_warnings.join(', ') }}
        </div>

        <template v-if="prodDeps.length">
          <div class="print-subsection">Production Dependencies{{ prodDeps.length >= 40 ? ' — top 40' : '' }}</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>Package</th><th>Version Spec</th><th>Source</th></tr></thead>
            <tbody>
              <tr v-for="d in prodDeps" :key="d.name + d.source">
                <td><strong>{{ d.name }}</strong></td>
                <td class="print-table__mono">{{ d.version_spec || '—' }}</td>
                <td class="print-table__muted">{{ d.source }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-if="devDeps.length">
          <div class="print-subsection">Dev Dependencies{{ devDeps.length >= 20 ? ' — top 20' : '' }}</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>Package</th><th>Version Spec</th><th>Source</th></tr></thead>
            <tbody>
              <tr v-for="d in devDeps" :key="d.name + d.source">
                <td>{{ d.name }}</td>
                <td class="print-table__mono">{{ d.version_spec || '—' }}</td>
                <td class="print-table__muted">{{ d.source }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-if="result.dependencies?.docker_issues?.length">
          <div class="print-subsection">Docker Issues</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>File</th><th>Issue</th></tr></thead>
            <tbody>
              <tr v-for="(d, i) in result.dependencies.docker_issues" :key="i">
                <td class="print-table__mono">{{ d.file }}</td>
                <td>{{ d.issue }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ══ §ARCHITECTURE ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.arch }}</span>
          <h2 class="print-section__title">Architecture</h2>
        </div>

        <div class="print-stat-grid print-stat-grid--sm">
          <div class="print-stat">
            <div class="print-stat__value">{{ result.graph.node_count }}</div>
            <div class="print-stat__label">Modules</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ result.graph.edge_count }}</div>
            <div class="print-stat__label">Edges</div>
          </div>
          <div class="print-stat">
            <div :class="['print-stat__value', result.graph.cycle_count > 0 ? 'print-risk--high' : '']">
              {{ result.graph.cycle_count }}
            </div>
            <div class="print-stat__label">Cycles</div>
          </div>
          <div class="print-stat">
            <div :class="['print-stat__value', (result.graph.god_modules?.length ?? 0) > 0 ? 'print-risk--medium' : '']">
              {{ result.graph.god_modules?.length ?? 0 }}
            </div>
            <div class="print-stat__label">God Modules</div>
          </div>
        </div>

        <template v-if="result.graph.cycles?.length">
          <div class="print-subsection">Dependency Cycles ({{ result.graph.cycle_count }})</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>#</th><th>Cycle Path</th></tr></thead>
            <tbody>
              <tr v-for="(cycle, i) in result.graph.cycles.slice(0, 10)" :key="i">
                <td class="print-table__muted">{{ i + 1 }}</td>
                <td class="print-table__mono" style="font-size:0.72rem;word-break:break-all">{{ cycle.join(' → ') }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <div v-if="godModules.length" style="margin-top:0.5rem;margin-bottom:1rem">
          <div class="print-subsection">God Modules</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>Module</th><th>In-degree</th></tr></thead>
            <tbody>
              <tr v-for="m in godModules" :key="m.module">
                <td class="print-table__mono">{{ m.module }}</td>
                <td>{{ m.in_degree }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hotFiles.length" style="margin-top:0.5rem">
          <div class="print-subsection">Hot Files</div>
          <table class="print-table print-table--bordered" style="width:100%">
            <thead><tr><th>File</th><th style="width:6rem">Commits</th></tr></thead>
            <tbody>
              <tr v-for="f in hotFiles" :key="f.file">
                <td class="print-table__mono">{{ f.file }}</td>
                <td>{{ f.commit_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- ══ §CODE QUALITY ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.codeQuality }}</span>
          <h2 class="print-section__title">Code Quality</h2>
        </div>

        <div class="print-stat-grid print-stat-grid--sm">
          <div class="print-stat">
            <div class="print-stat__value">{{ codeQuality.complexity?.files_over_threshold ?? 0 }}</div>
            <div class="print-stat__label">Complexity Hotspots</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ codeQuality.deadCode?.count ?? 0 }}</div>
            <div class="print-stat__label">Unreferenced Files</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ codeQuality.junkFiles?.count ?? 0 }}</div>
            <div class="print-stat__label">Clutter Files</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ formatPct(codeQuality.testCoverage?.test_ratio ?? null) }}</div>
            <div class="print-stat__label">Test Ratio</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ codeQuality.testCoverage?.framework_detected ?? '—' }}</div>
            <div class="print-stat__label">Test Framework</div>
          </div>
        </div>

        <template v-if="(codeQuality.complexity?.hotspots?.length ?? 0) > 0">
          <div class="print-subsection">Top Complexity Hotspots</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>File</th><th>LOC</th><th>Adjacent Test</th></tr></thead>
            <tbody>
              <tr v-for="f in (codeQuality.complexity?.hotspots ?? []).slice(0, 12)" :key="f.file">
                <td class="print-table__mono">{{ f.file }}</td>
                <td>{{ f.loc }}</td>
                <td>{{ f.has_adjacent_test ? 'Yes' : 'No' }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-if="(codeQuality.testCoverage?.untested_dirs?.length ?? 0) > 0">
          <div class="print-subsection">Directories Missing Tests</div>
          <table class="print-table print-table--bordered">
            <thead><tr><th>Directory</th><th>Source Files</th></tr></thead>
            <tbody>
              <tr v-for="d in (codeQuality.testCoverage?.untested_dirs ?? []).slice(0, 12)" :key="d.path">
                <td class="print-table__mono">{{ d.path }}</td>
                <td>{{ d.source_files }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <div
          v-if="(codeQuality.complexity?.hotspots?.length ?? 0) === 0 && (codeQuality.testCoverage?.untested_dirs?.length ?? 0) === 0"
          class="print-clear"
        >
          No major code quality hotspots detected by current static checks.
        </div>
      </section>

      <!-- ══ §DEVOPS ══ -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.devops }}</span>
          <h2 class="print-section__title">DevOps</h2>
        </div>

        <div class="print-stat-grid print-stat-grid--sm">
          <div class="print-stat">
            <div class="print-stat__value">{{ devOps.cicd?.workflow_count ?? 0 }}</div>
            <div class="print-stat__label">CI Workflows</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ devOps.containers?.dockerfile_count ?? 0 }}</div>
            <div class="print-stat__label">Dockerfiles</div>
          </div>
          <div class="print-stat">
            <div :class="['print-stat__value', (devOps.containers?.total_issues ?? 0) > 0 ? 'print-risk--medium' : '']">
              {{ devOps.containers?.total_issues ?? 0 }}
            </div>
            <div class="print-stat__label">Container Issues</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ devOps.changelog?.found ? 'Present' : 'Missing' }}</div>
            <div class="print-stat__label">Changelog</div>
          </div>
        </div>

        <table class="print-table print-table--bordered print-table--compact">
          <tbody>
            <tr>
              <td class="print-table__key">CI System</td>
              <td>{{ devOps.cicd?.system ?? 'Not detected' }}</td>
              <td class="print-table__key">Runs Tests</td>
              <td>{{ devOps.cicd?.summary?.has_tests ? 'Yes' : 'No' }}</td>
            </tr>
            <tr>
              <td class="print-table__key">Runs Lint</td>
              <td>{{ devOps.cicd?.summary?.has_lint ? 'Yes' : 'No' }}</td>
              <td class="print-table__key">Deploy Job</td>
              <td>{{ devOps.cicd?.summary?.has_deploy ? 'Yes' : 'No' }}</td>
            </tr>
            <tr>
              <td class="print-table__key">Changelog Format</td>
              <td>{{ devOps.changelog?.format ?? 'none' }}</td>
              <td class="print-table__key">Days Since Changelog Update</td>
              <td>{{ devOps.changelog?.days_stale ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ══ §SUB-PROJECTS (conditional) ══ -->
      <section v-if="subProjects.length" class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.subprojects }}</span>
          <h2 class="print-section__title">Sub-projects</h2>
        </div>

        <div v-for="sp in subProjects" :key="sp.name" style="margin-bottom:1.5rem">
          <div class="print-subsection">{{ sp.name }} <span style="font-weight:400;color:#666">— {{ sp.path }}</span></div>

          <div class="print-stat-grid print-stat-grid--sm" style="margin-bottom:0.75rem">
            <div v-if="sp.oss_score" class="print-stat">
              <div class="print-stat__value">{{ sp.oss_score.score }}</div>
              <div class="print-stat__label">Health Score ({{ sp.oss_score.label }})</div>
            </div>
            <div class="print-stat">
              <div class="print-stat__value">{{ sp.languages.join(', ') || '—' }}</div>
              <div class="print-stat__label">Languages</div>
            </div>
            <div class="print-stat">
              <div class="print-stat__value">{{ (sp.dependencies?.dependencies ?? []).filter(d => !d.dev).length }}</div>
              <div class="print-stat__label">Prod Deps</div>
            </div>
            <div v-if="sp.security?.issue_count != null" class="print-stat">
              <div :class="['print-stat__value', sp.security.issue_count > 0 ? 'print-risk--high' : '']">
                {{ sp.security.issue_count }}
              </div>
              <div class="print-stat__label">Security Issues</div>
            </div>
          </div>

          <div v-if="sp.tech_stack?.length" style="font-size:0.8125rem;color:#555;margin-bottom:0.25rem">
            Stack: {{ sp.tech_stack.join(', ') }}
          </div>
        </div>
      </section>

      <!-- ══ §CONTRIBUTING (conditional) ══ -->
      <section v-if="opportunities.length" class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">{{ sectionNums.contributing }}</span>
          <h2 class="print-section__title">Contributing Opportunities</h2>
        </div>

        <table class="print-table print-table--bordered">
          <thead>
            <tr><th>Title</th><th>Difficulty</th><th>Category</th><th>Effort</th></tr>
          </thead>
          <tbody>
            <tr v-for="op in opportunities" :key="op.id">
              <td>{{ op.title }}</td>
              <td>
                <span
                  class="print-badge"
                  :style="{ color: difficultyColor[op.difficulty], borderColor: difficultyColor[op.difficulty], background: 'transparent' }"
                >{{ op.difficulty }}</span>
              </td>
              <td class="print-table__muted">{{ op.category }}</td>
              <td class="print-table__muted">{{ op.effort_estimate ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ══ REPORT FOOTER ══ -->
      <div class="print-report-footer">
        <div class="print-report-footer__left">
          <div class="print-report-footer__brand">Atlas Insight</div>
          <div class="print-report-footer__meta">
            {{ run.repo_owner }}/{{ run.repo_name }}<template v-if="run.branch"> @ {{ run.branch }}</template> · {{ formatDate(run.completed_at) }} · {{ run.id }}
          </div>
        </div>
        <div class="print-report-footer__disclaimer">
          Automated static analysis only. Does not constitute a security audit, code review,
          or professional assessment. Apply domain expertise when interpreting results.
        </div>
      </div>

    </template>
  </div>
</template>
