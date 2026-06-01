<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import type { AnalysisRun, RunResult } from '../stores/analysis'

const route = useRoute()
const runId = route.params.runId as string

const run = ref<AnalysisRun | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  document.documentElement.setAttribute('data-layout', 'print')
  try {
    const { data } = await axios.get(`/api/v1/repositories/runs/${runId}`)
    run.value = data
  } catch {
    error.value = 'Failed to load analysis data.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.documentElement.removeAttribute('data-layout')
})

const result = computed<RunResult | null>(() => {
  const r = run.value?.result
  if (!r || r.error) return null
  return r
})

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

const overallScore = computed(() => {
  if (!result.value?.heuristics?.length) return null
  return Math.round(
    result.value.heuristics.reduce((s, h) => s + h.score, 0) / result.value.heuristics.length
  )
})

const sortedSignals = computed(() =>
  result.value ? [...result.value.heuristics].sort((a, b) => b.score - a.score) : []
)

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

const langBarColors = ['#0969da', '#2da44e', '#e36209', '#8250df']

function triggerPrint() { window.print() }
function triggerClose() { window.close() }

const topLangs = computed(() => result.value?.structure?.languages?.slice(0, 5) ?? [])

const prodDeps = computed(() =>
  (result.value?.dependencies?.dependencies ?? [])
    .filter(d => !d.dev)
    .slice(0, 40)
)

const devDeps = computed(() =>
  (result.value?.dependencies?.dependencies ?? [])
    .filter(d => d.dev)
    .slice(0, 20)
)

const securityIssues = computed(() => {
  const issues = result.value?.security?.issues ?? []
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  return [...issues].sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))
})

const vulns = computed(() => result.value?.security?.vulnerabilities ?? [])

const godModules = computed(() => result.value?.graph?.god_modules?.slice(0, 15) ?? [])
const hotFiles = computed(() => result.value?.structure?.hot_files?.slice(0, 15) ?? [])

const opportunities = computed(() =>
  (result.value?.contribution_opportunities ?? []).slice(0, 20)
)

const difficultyColor: Record<string, string> = {
  beginner: '#2da44e',
  intermediate: '#d97706',
  advanced: '#dc2626',
}
</script>

<template>
  <div class="print-view">

    <!-- Screen-only controls -->
    <div class="print-controls">
      <div class="print-controls__inner">
        <span class="print-controls__brand">Atlas Insight</span>
        <span class="print-controls__label">Analysis Report Preview</span>
        <div class="print-controls__actions">
          <button class="print-controls__btn print-controls__btn--primary" @click="triggerPrint">
            ⎙ Print / Save PDF
          </button>
          <button class="print-controls__btn" @click="triggerClose">
            ✕ Close
          </button>
        </div>
      </div>
    </div>

    <!-- Loading / Error -->
    <div v-if="loading" class="print-state">Loading analysis…</div>
    <div v-else-if="error || !result" class="print-state print-state--error">
      {{ error ?? 'Analysis data unavailable.' }}
    </div>

    <template v-else-if="result && run">

      <!-- ── COVER ── -->
      <section class="print-cover">
        <div class="print-cover__brand">Atlas Insight</div>
        <div class="print-cover__report-label">Repository Analysis Report</div>
        <div class="print-cover__rule" />
        <h1 class="print-cover__repo">{{ run.repo_owner }} / {{ run.repo_name }}</h1>
        <div class="print-cover__meta">
          <div class="print-cover__meta-row">
            <span class="print-cover__meta-key">Repository</span>
            <span class="print-cover__meta-val">{{ run.repo_url }}</span>
          </div>
          <div class="print-cover__meta-row">
            <span class="print-cover__meta-key">Analyzed</span>
            <span class="print-cover__meta-val">{{ formatDate(run.completed_at) }}</span>
          </div>
          <div class="print-cover__meta-row">
            <span class="print-cover__meta-key">Run ID</span>
            <span class="print-cover__meta-val print-cover__run-id">{{ run.id }}</span>
          </div>
          <div v-if="result.github_meta?.primary_language" class="print-cover__meta-row">
            <span class="print-cover__meta-key">Primary Language</span>
            <span class="print-cover__meta-val">{{ result.github_meta.primary_language }}</span>
          </div>
          <div v-if="result.classification" class="print-cover__meta-row">
            <span class="print-cover__meta-key">Project Health</span>
            <span class="print-cover__meta-val">{{ result.classification.project_health.label }}</span>
          </div>
        </div>
        <div v-if="result.github_meta?.github_description" class="print-cover__desc">
          {{ result.github_meta.github_description }}
        </div>
        <div v-if="result.github_meta?.topics?.length" class="print-cover__topics">
          <span v-for="t in result.github_meta.topics" :key="t" class="print-cover__topic">{{ t }}</span>
        </div>
        <div class="print-cover__footer">Generated by Atlas Insight · {{ formatDate(run.completed_at) }}</div>
      </section>

      <!-- ── SECTION 1: EXECUTIVE SUMMARY ── -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">01</span>
          <h2 class="print-section__title">Executive Summary</h2>
        </div>

        <!-- Key stats -->
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
            <div class="print-stat__label">Days Since Last Commit</div>
          </div>
          <div v-if="result.structure?.total_lines" class="print-stat">
            <div class="print-stat__value">{{ formatNum(result.structure.total_lines) }}</div>
            <div class="print-stat__label">Lines of Code</div>
          </div>
          <div v-if="overallScore !== null" class="print-stat">
            <div :class="['print-stat__value', `print-stat__value--${scoreLevel(overallScore)}`]">
              {{ overallScore }}<span class="print-stat__unit">/100</span>
            </div>
            <div class="print-stat__label">Composite Risk Score</div>
          </div>
          <div v-if="result.structure?.test_ratio != null" class="print-stat">
            <div class="print-stat__value">{{ formatPct(result.structure.test_ratio) }}</div>
            <div class="print-stat__label">Test Coverage</div>
          </div>
        </div>

        <!-- Classification -->
        <div v-if="result.classification" class="print-classify">
          <div class="print-classify__row">
            <div class="print-classify__item">
              <span class="print-classify__key">Health</span>
              <span class="print-classify__val">{{ result.classification.project_health.label }}</span>
            </div>
            <div class="print-classify__item">
              <span class="print-classify__key">Contribution</span>
              <span class="print-classify__val">{{ result.classification.contribution_difficulty.label }}</span>
            </div>
            <div class="print-classify__item">
              <span class="print-classify__key">Complexity</span>
              <span class="print-classify__val">{{ result.classification.code_complexity.label }}</span>
            </div>
            <div class="print-classify__item">
              <span class="print-classify__key">Documentation</span>
              <span class="print-classify__val">{{ result.classification.documentation_grade.label }}</span>
            </div>
          </div>
          <div v-if="result.classification.tags?.length" class="print-classify__tags">
            <span v-for="tag in result.classification.tags" :key="tag" class="print-classify__tag">{{ tag }}</span>
          </div>
        </div>

        <!-- GitHub stats -->
        <div v-if="result.github_meta" class="print-gh-stats">
          <table class="print-table print-table--compact">
            <tbody>
              <tr v-if="result.github_meta.stars">
                <td class="print-table__key">Stars</td>
                <td>{{ formatNum(result.github_meta.stars) }}</td>
                <td class="print-table__key">Forks</td>
                <td>{{ formatNum(result.github_meta.forks) }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Open Issues</td>
                <td>{{ formatNum(result.github_meta.open_issues) }}</td>
                <td class="print-table__key">Open PRs</td>
                <td>{{ result.github_meta.open_prs ?? '—' }}</td>
              </tr>
              <tr v-if="result.github_meta.license_name">
                <td class="print-table__key">License</td>
                <td>{{ result.github_meta.license_spdx ?? result.github_meta.license_name }}</td>
                <td class="print-table__key">Default Branch</td>
                <td>{{ result.github_meta.default_branch }}</td>
              </tr>
              <tr v-if="result.github_meta.created_at">
                <td class="print-table__key">Created</td>
                <td>{{ formatDate(result.github_meta.created_at) }}</td>
                <td class="print-table__key">Last Push</td>
                <td>{{ formatDate(result.github_meta.pushed_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Language breakdown -->
        <div v-if="topLangs.length" class="print-langs">
          <div class="print-langs__bar">
            <div
              v-for="(lang, i) in topLangs"
              :key="lang.name"
              :style="{ width: `${lang.pct}%`, background: langBarColors[i] ?? '#888' }"
              class="print-langs__seg"
              :title="`${lang.name}: ${lang.pct}%`"
            />
          </div>
          <div class="print-langs__legend">
            <span v-for="(lang, i) in topLangs" :key="lang.name" class="print-langs__item">
              <span class="print-langs__dot" :style="{ background: langBarColors[i] ?? '#888' }" />
              {{ lang.name }} {{ lang.pct }}%
            </span>
          </div>
        </div>

        <!-- Abandoned notice -->
        <div v-if="result.commits.abandoned" class="print-alert print-alert--warn">
          Repository appears abandoned — no commits in 365+ days.
        </div>
      </section>

      <!-- ── SECTION 2: HEALTH SIGNALS ── -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">02</span>
          <h2 class="print-section__title">Health Signals</h2>
        </div>
        <p class="print-section__intro">
          Automated signals about project activity, health, and contributor patterns.
          Scores are 0–100 where higher = greater risk or concern.
        </p>

        <div v-if="overallScore !== null" class="print-composite">
          Composite Score:
          <strong :class="`print-risk--${scoreLevel(overallScore)}`">{{ overallScore }} / 100</strong>
          — {{ scoreRiskLabel(overallScore) }}
        </div>

        <table class="print-table">
          <thead>
            <tr>
              <th>Signal</th>
              <th class="print-table__num-col">Score</th>
              <th class="print-table__bar-col">Risk</th>
              <th>Risk Level</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sortedSignals" :key="s.signal">
              <td>{{ s.label }}</td>
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

        <!-- Signal descriptions -->
        <div class="print-signal-details">
          <div v-for="s in sortedSignals" :key="`desc-${s.signal}`" class="print-signal-detail">
            <strong>{{ s.label }}:</strong> {{ s.description }}
            <template v-if="s.items?.length">
              <ul class="print-signal-items">
                <li v-for="item in s.items.slice(0, 5)" :key="item">{{ item }}</li>
              </ul>
            </template>
          </div>
        </div>
      </section>

      <!-- ── SECTION 3: SECURITY ── -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">03</span>
          <h2 class="print-section__title">Security</h2>
        </div>
        <p class="print-section__intro">
          Automated pattern matching only — not a full security audit.
          Always consult a security professional for production systems.
        </p>

        <div v-if="result.security" class="print-security-meta">
          <table class="print-table print-table--compact">
            <tbody>
              <tr>
                <td class="print-table__key">Security Score</td>
                <td>
                  <strong :class="`print-risk--${scoreLevel(result.security.score)}`">
                    {{ result.security.score }} / 100
                  </strong>
                </td>
                <td class="print-table__key">.gitignore</td>
                <td>{{ result.security.gitignore_exists ? 'Present' : 'Missing' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Security Policy</td>
                <td>{{ result.structure?.has_security_policy ? (result.structure.security_policy_file ?? 'Present') : 'Not found' }}</td>
                <td class="print-table__key">Gitignore Gaps</td>
                <td>{{ result.security.gitignore_gaps?.length ? result.security.gitignore_gaps.join(', ') : 'None' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <template v-if="securityIssues.length">
          <h3 class="print-subsection">Patterns Detected ({{ securityIssues.length }})</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Type</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(issue, i) in securityIssues" :key="i">
                <td>
                  <span :class="['print-badge', `print-badge--${issue.severity}`]">{{ issue.severity }}</span>
                </td>
                <td>{{ issue.type }}</td>
                <td>{{ issue.detail }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <div v-else class="print-clear">
          ✓ No common security patterns detected.
        </div>

        <template v-if="vulns.length">
          <h3 class="print-subsection">Dependency Vulnerabilities — OSV.dev ({{ vulns.length }})</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>Package</th>
                <th>Version</th>
                <th>CVE ID</th>
                <th>Severity</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="v in vulns" :key="v.vuln_id + v.name">
                <td><strong>{{ v.name }}</strong></td>
                <td class="print-table__mono">{{ v.version }}</td>
                <td class="print-table__mono">{{ v.vuln_id }}</td>
                <td>
                  <span :class="['print-badge', v.severity?.toLowerCase().includes('critical') || v.severity?.toLowerCase().includes('high') ? 'print-badge--critical' : v.severity?.toLowerCase().includes('medium') ? 'print-badge--medium' : 'print-badge--low']">
                    {{ v.severity ?? 'unknown' }}
                  </span>
                </td>
                <td>{{ v.summary }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <div v-else class="print-clear">
          ✓ No known CVEs detected in scanned dependencies.
        </div>
      </section>

      <!-- ── SECTION 4: PROJECT STRUCTURE ── -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">04</span>
          <h2 class="print-section__title">Project Structure</h2>
        </div>

        <div v-if="result.structure" class="print-two-col">
          <table class="print-table print-table--compact">
            <tbody>
              <tr>
                <td class="print-table__key">Total Files</td>
                <td>{{ formatNum(result.structure.total_files) }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Lines of Code</td>
                <td>{{ formatNum(result.structure.total_lines) }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Test Files</td>
                <td>{{ formatNum(result.structure.test_files) }} ({{ formatPct(result.structure.test_ratio) }})</td>
              </tr>
              <tr>
                <td class="print-table__key">Repository Age</td>
                <td>{{ result.structure.repo_age_days ? `${result.structure.repo_age_days.toLocaleString()} days` : '—' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Bus Factor</td>
                <td>{{ result.structure.bus_factor }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Releases</td>
                <td>{{ result.structure.release_count }}</td>
              </tr>
              <tr v-if="result.structure.last_release">
                <td class="print-table__key">Last Release</td>
                <td>{{ result.structure.last_release.name }} ({{ formatDate(result.structure.last_release.date) }})</td>
              </tr>
            </tbody>
          </table>

          <table class="print-table print-table--compact">
            <tbody>
              <tr>
                <td class="print-table__key">CI / CD</td>
                <td>{{ result.structure.has_ci ? (result.structure.ci_systems?.join(', ') || 'Yes') : 'Not detected' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Docker</td>
                <td>{{ result.structure.has_docker ? 'Present' : 'Not found' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Lint Config</td>
                <td>{{ result.structure.has_lint_config ? 'Present' : 'Not found' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">License</td>
                <td>{{ result.structure.license_type ?? (result.structure.license_file ?? 'Not found') }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Contributing Guide</td>
                <td>{{ result.structure.has_contributing ? (result.structure.contributing_file ?? 'Present') : 'Not found' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Code of Conduct</td>
                <td>{{ result.structure.has_coc ? (result.structure.coc_file ?? 'Present') : 'Not found' }}</td>
              </tr>
              <tr>
                <td class="print-table__key">Changelog</td>
                <td>{{ result.structure.has_changelog ? (result.structure.changelog_file ?? 'Present') : 'Not found' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Tech stack -->
        <div v-if="result.structure?.tech_stack?.length" class="print-tech-stack">
          <span class="print-table__key" style="display:block;margin-bottom:0.35rem">Tech Stack</span>
          <span v-for="t in result.structure.tech_stack" :key="t" class="print-classify__tag">{{ t }}</span>
        </div>

        <!-- Top contributors -->
        <template v-if="result.structure?.top_contributors?.length">
          <h3 class="print-subsection">Top Contributors</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Author</th>
                <th>Files Touched</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in result.structure.top_contributors.slice(0, 10)" :key="c.author">
                <td class="print-table__muted">{{ i + 1 }}</td>
                <td>{{ c.author }}</td>
                <td>{{ formatNum(c.files_touched) }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- Stale branches -->
        <template v-if="(result.structure?.stale_branches?.length ?? 0) > 0">
          <h3 class="print-subsection">
            Stale Branches ({{ result.structure!.stale_branch_count }})
          </h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>Branch</th>
                <th>Last Commit</th>
                <th>Days Stale</th>
              </tr>
            </thead>
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

      <!-- ── SECTION 5: DEPENDENCIES ── -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">05</span>
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
            <div :class="['print-stat__value', (result.security?.vulnerabilities?.length ?? 0) > 0 ? 'print-risk--high' : '']">
              {{ result.security?.vulnerabilities?.length ?? 0 }}
            </div>
            <div class="print-stat__label">CVEs Found</div>
          </div>
        </div>

        <template v-if="result.dependencies?.missing_lockfile_warnings?.length">
          <div class="print-alert print-alert--warn">
            Missing lockfile{{ result.dependencies.missing_lockfile_warnings.length > 1 ? 's' : '' }}:
            {{ result.dependencies.missing_lockfile_warnings.join(', ') }}
          </div>
        </template>

        <template v-if="prodDeps.length">
          <h3 class="print-subsection">Production Dependencies{{ prodDeps.length >= 40 ? ' (top 40)' : '' }}</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>Package</th>
                <th>Version Spec</th>
                <th>Source</th>
              </tr>
            </thead>
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
          <h3 class="print-subsection">Dev Dependencies{{ devDeps.length >= 20 ? ' (top 20)' : '' }}</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>Package</th>
                <th>Version Spec</th>
                <th>Source</th>
              </tr>
            </thead>
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
          <h3 class="print-subsection">Docker Issues</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Issue</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(d, i) in result.dependencies.docker_issues" :key="i">
                <td class="print-table__mono">{{ d.file }}</td>
                <td>{{ d.issue }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ── SECTION 6: ARCHITECTURE ── -->
      <section class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">06</span>
          <h2 class="print-section__title">Architecture</h2>
        </div>

        <div class="print-stat-grid print-stat-grid--sm">
          <div class="print-stat">
            <div class="print-stat__value">{{ result.graph.node_count }}</div>
            <div class="print-stat__label">Modules</div>
          </div>
          <div class="print-stat">
            <div class="print-stat__value">{{ result.graph.edge_count }}</div>
            <div class="print-stat__label">Dependencies</div>
          </div>
          <div class="print-stat">
            <div :class="['print-stat__value', result.graph.cycle_count > 0 ? 'print-risk--high' : '']">
              {{ result.graph.cycle_count }}
            </div>
            <div class="print-stat__label">Cycles</div>
          </div>
          <div class="print-stat">
            <div :class="['print-stat__value', result.graph.god_modules?.length > 0 ? 'print-risk--medium' : '']">
              {{ result.graph.god_modules?.length ?? 0 }}
            </div>
            <div class="print-stat__label">God Modules</div>
          </div>
        </div>

        <template v-if="result.graph.cycles?.length">
          <h3 class="print-subsection">Dependency Cycles ({{ result.graph.cycle_count }})</h3>
          <table class="print-table">
            <thead><tr><th>#</th><th>Cycle</th></tr></thead>
            <tbody>
              <tr v-for="(cycle, i) in result.graph.cycles.slice(0, 10)" :key="i">
                <td class="print-table__muted">{{ i + 1 }}</td>
                <td class="print-table__mono" style="font-size:0.75rem">{{ cycle.join(' → ') }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-if="godModules.length">
          <h3 class="print-subsection">God Modules (high fan-in)</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>Module</th>
                <th>In-degree</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in godModules" :key="m.module">
                <td class="print-table__mono">{{ m.module }}</td>
                <td>{{ m.in_degree }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-if="hotFiles.length">
          <h3 class="print-subsection">Hot Files (most commits)</h3>
          <table class="print-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Commits</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in hotFiles" :key="f.file">
                <td class="print-table__mono">{{ f.file }}</td>
                <td>{{ f.commit_count }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ── SECTION 7: CONTRIBUTING OPPORTUNITIES ── -->
      <section v-if="opportunities.length" class="print-section">
        <div class="print-section__header">
          <span class="print-section__num">07</span>
          <h2 class="print-section__title">Contributing Opportunities</h2>
        </div>
        <p class="print-section__intro">
          Identified opportunities for contribution based on repository analysis.
        </p>

        <table class="print-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Difficulty</th>
              <th>Category</th>
              <th>Effort</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="op in opportunities" :key="op.id">
              <td>{{ op.title }}</td>
              <td>
                <span class="print-badge" :style="{ color: difficultyColor[op.difficulty], borderColor: difficultyColor[op.difficulty] }">
                  {{ op.difficulty }}
                </span>
              </td>
              <td class="print-table__muted">{{ op.category }}</td>
              <td class="print-table__muted">{{ op.effort_estimate ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ── REPORT FOOTER ── -->
      <div class="print-report-footer">
        <div class="print-report-footer__brand">Atlas Insight</div>
        <div class="print-report-footer__meta">
          {{ run.repo_owner }}/{{ run.repo_name }} · {{ formatDate(run.completed_at) }} · Run {{ run.id }}
        </div>
        <div class="print-report-footer__disclaimer">
          This report is generated by automated static analysis. It does not constitute a security audit,
          code review, or professional assessment. Always apply domain expertise when interpreting results.
        </div>
      </div>

    </template>
  </div>
</template>
