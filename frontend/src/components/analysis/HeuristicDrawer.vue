<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import type { HeuristicSignal, HeuristicSignalKey, RunResult } from '../../stores/analysis'

const props = defineProps<{ signal: HeuristicSignal | null; result?: RunResult }>()
const emit = defineEmits<{ close: [] }>()

const isClosedSource = computed(
  () => (props.result?.scoring_mode ?? props.result?.oss_score?.mode) === 'closed_source',
)

interface SignalInfo {
  overview: string
  raises: string[]
  guidance: string
}

const SIGNAL_INFO: Record<HeuristicSignalKey, SignalInfo> = {
  burnout: {
    overview:
      'Measures how much the team\'s commit activity and contributor count have dropped relative to their historical peak. High scores suggest a project may be running out of momentum or that key contributors have stepped back.',
    raises: [
      'Active contributor count has fallen significantly from peak',
      'Commit frequency has declined compared to historical baseline',
      'Both trends happening simultaneously amplifies the score',
    ],
    guidance:
      'Look at the contributor churn chart to see when contributors left. A single large drop often signals a fork, organizational change, or burnout event rather than slow natural decline.',
  },
  abandonment_risk: {
    overview:
      'Tracks how long the repo has been silent — no commits to the main branch. Projects that stop receiving commits are at increasing risk of being unmaintained, which affects security patching, bug fixes, and compatibility with newer tooling.',
    raises: [
      'No commits in the last 90+ days',
      'Days since last commit exceeding 180, 365, or 730 days',
      'Abandoned flag set (extreme decay in activity)',
    ],
    guidance:
      'Check the commit timeline to see if activity is just seasonal or truly stopped. Some projects are "done" and intentionally unmaintained — look at open issues and the README for signals about maintenance intent.',
  },
  monolith_growth: {
    overview:
      'Detects structural complexity in the import graph — files that everything depends on (god modules) and circular dependencies. These patterns make the codebase harder to refactor, test in isolation, and onboard into.',
    raises: [
      'High-in-degree modules (imported by many other files)',
      'Circular dependency chains between modules',
      'Both scale linearly with the score — more = worse',
    ],
    guidance:
      'God modules are often utilities, base classes, or shared constants. Not all are problems — a single well-designed utility module is fine. Circular dependencies are usually worth fixing as they prevent tree-shaking and complicate testing.',
  },
  dependency_health: {
    overview:
      'Evaluates risk from the dependency surface: deprecated Docker base images, missing lockfiles, and sheer dependency count. Each contributes to supply chain risk and reproducibility concerns.',
    raises: [
      'Deprecated or end-of-life Docker base images in Dockerfiles',
      'No lockfile for a package manager that should have one',
      'Very high total dependency count (200+ adds marginal risk score)',
    ],
    guidance:
      'Outdated Docker bases often have known CVEs. Missing lockfiles mean builds aren\'t reproducible and CI/CD results may differ from development. Large dependency trees increase the blast radius of supply chain attacks.',
  },
  documentation_quality: {
    overview:
      'Assesses how well the project documents itself for new contributors and users. Evaluated from README content and the presence of community health files.',
    raises: [
      'No README, or README is very short',
      'Missing installation or usage sections',
      'No changelog or contributing guide referenced',
      'No CONTRIBUTING.md file in the repo',
    ],
    guidance:
      'Good documentation is the #1 factor in whether a new contributor can make their first PR. Even a minimal README with install + usage instructions makes a huge difference. A CONTRIBUTING file signals the project is welcoming to outside contributions.',
  },
  ci_health: {
    overview:
      'Looks at whether the project has automated quality checks in place: CI pipelines, linting, and a meaningful ratio of test files to source files.',
    raises: [
      'No CI configuration detected (GitHub Actions, Travis, CircleCI, etc.)',
      'No linting or code formatting config',
      'Very few test files relative to source files',
    ],
    guidance:
      'The test ratio is a proxy, not a coverage measurement — it counts test files vs source files. A project with thorough integration tests in few files may score worse than it deserves. CI without tests is still better than nothing.',
  },
  bus_factor_risk: {
    overview:
      'The bus factor is how many contributors you\'d need to "lose" before 80%+ of the codebase has no active knowledge holder. A bus factor of 1 means a single person holds almost all institutional knowledge.',
    raises: [
      '1–2 contributors responsible for the majority of file changes',
      'No distribution of ownership across the codebase',
      'Score is (5 − bus_factor) × 20, so 1 = 80 risk, 5+ = 0 risk',
    ],
    guidance:
      'A low bus factor isn\'t always a problem for solo projects, but it\'s a major risk for open source projects that depend on community continuity. Look at whether the top contributors are still active.',
  },
  security_hygiene: {
    overview:
      'Scans the git-tracked file list for accidentally committed secrets, certificates, or credentials, and checks the .gitignore for gaps that could lead to future leaks.',
    raises: [
      '.env files, private keys, or credential JSON committed to the repo',
      'No .gitignore present',
      '.gitignore missing recommended patterns (node_modules, .env, *.pem, etc.)',
    ],
    guidance:
      'Any committed secret should be treated as compromised — rotate it immediately even if the repo is private. A private repo can become public, and git history persists. Use git-filter-repo or BFG to scrub secrets from history.',
  },
  release_cadence: {
    overview:
      'Measures how frequently the project cuts formal releases (git tags) and how recently the last release was. Consistent releases signal active maintenance and give downstream users a reliable update path.',
    raises: [
      'No git tags / releases at all',
      'Last release more than 12 months ago',
      'Last release more than 2 years ago',
    ],
    guidance:
      'No releases doesn\'t always mean a project is unmaintained — some projects ship continuously from main without tagging. But for library authors and tools, regular releases help users know what they\'re getting and simplify changelogs.',
  },
  community_health: {
    overview:
      'Checks for the presence of key community health files that signal whether a project is set up to welcome and protect contributors. Missing files don\'t mean bad code, but they do affect how welcoming a project feels to new participants.',
    raises: [
      'No LICENSE file — legally unclear if the code can be used',
      'No CONTRIBUTING guide — harder for newcomers to know how to help',
      'No SECURITY policy — no clear path to report vulnerabilities',
      'No Code of Conduct — signals less intentional community stewardship',
      'No CHANGELOG — harder to understand what changed between versions',
    ],
    guidance:
      'A missing LICENSE is the most critical gap — without one, the default is "all rights reserved" and the code technically can\'t be legally used. Adding a LICENSE, CONTRIBUTING, and SECURITY file takes under an hour and substantially improves perceived project health.',
  },
  commit_velocity: {
    overview:
      'Compares the average commit frequency over the last 3 months to the prior 3 months. A declining trend may indicate reduced interest, shifting priorities, or approaching project completion.',
    raises: [
      'Recent 3-month commit average is significantly below the prior 3 months',
      'Sharp decline (>60% drop) scores high risk',
      'Needs at least 6 months of commit history to compute',
    ],
    guidance:
      'Context matters: a summer slowdown or post-release quiet period is normal. Look at the commit timeline chart to distinguish a one-time dip from a sustained trend. Rising velocity is a strong signal of active investment.',
  },
  license_risk: {
    overview:
      'Checks whether the repository has a machine-readable open source license and flags compatibility concerns when the detected SPDX identifier is a restrictive or copyleft license.',
    raises: [
      'No LICENSE file detected — repo is implicitly all-rights-reserved',
      'License uses a restrictive or copyleft SPDX identifier',
      'License file exists but is not a recognized SPDX expression',
    ],
    guidance:
      'A missing license is the most impactful thing to fix — without one, downstream users cannot legally use, modify, or redistribute the code even if it is public. Adding an MIT, Apache-2.0, or similar permissive license takes minutes and removes a significant adoption barrier.',
  },
  complexity_debt: {
    overview:
      'Counts files that exceed a line-of-code threshold and flags high-complexity files that lack adjacent test files. Large, untested files are the highest-risk items for future refactoring.',
    raises: [
      'Files exceeding 500 LOC threshold',
      'High-LOC files with no adjacent test file',
      'Score scales with both the count and the size of over-threshold files',
    ],
    guidance:
      'Large files are not automatically a problem — a 1000-line file with clear structure and full test coverage is fine. The concern is large files with no tests and high change frequency, which combine complexity, risk, and regressions.',
  },
  test_coverage: {
    overview:
      'Estimates test coverage by comparing the ratio of test files to source files across directories. Directories with source code but no test files are flagged as untested coverage gaps.',
    raises: [
      'Very low test-to-source file ratio across the repo',
      'Source directories with no corresponding test files',
      'Score is higher when untested directories contain many files',
    ],
    guidance:
      'This metric counts files, not lines or branches — a directory with 20 source files and 1 test file still counts as covered. Focus first on directories that are completely absent from testing, then on raising overall test file density.',
  },
  cicd_maturity: {
    overview:
      'Evaluates the quality of the CI/CD pipeline beyond just its existence — looking for test steps, lint steps, and a meaningful workflow configuration. A CI pipeline that only builds the app without running tests offers limited safety.',
    raises: [
      'No CI workflows configured',
      'CI configured but no test step detected in any workflow',
      'CI configured but no lint or format check step',
    ],
    guidance:
      'The most impactful addition is an automated test run on every push. Even a single `pytest` or `npm test` step in a GitHub Actions workflow catches regressions before they merge. Linting is a quick second step — most formatters run in under 10 seconds.',
  },
  container_hygiene: {
    overview:
      'Audits Dockerfiles for common security and best-practice issues: running as root, using deprecated or floating base image tags, missing health checks, and other patterns that increase container attack surface.',
    raises: [
      'Container process runs as root (no USER instruction)',
      'Base image uses a floating tag like :latest or :stable',
      'Other high-severity Dockerfile issues detected',
    ],
    guidance:
      'Running containers as root is the most common and impactful issue — add a non-root USER instruction before the CMD. Pinning base image tags (e.g. python:3.12.3-slim instead of python:latest) improves reproducibility and eliminates surprise dependency updates.',
  },
}

const info = computed(() =>
  props.signal ? SIGNAL_INFO[props.signal.signal] : null
)

function level(score: number) {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

function riskLabel(score: number) {
  if (score < 30) return 'Low Risk'
  if (score < 60) return 'Moderate Risk'
  return 'High Risk'
}

const ICONS: Record<HeuristicSignalKey, string> = {
  burnout: '🔥', abandonment_risk: '💤', monolith_growth: '🏗️',
  dependency_health: '📦', documentation_quality: '📝', ci_health: '⚙️',
  bus_factor_risk: '🚌', security_hygiene: '🔒', release_cadence: '🏷️',
  community_health: '🤝', commit_velocity: '📈',
  license_risk: '⚖️', complexity_debt: '🧩', test_coverage: '🧪',
  cicd_maturity: '🚀', container_hygiene: '🐳',
}

interface RepoInsightItem {
  text: string
  sub?: string
  highlight?: boolean
  monospace?: boolean
}

const repoInsight = computed<RepoInsightItem[] | null>(() => {
  if (!props.signal || !props.result) return null
  const r = props.result
  const sig = props.signal.signal
  const items: RepoInsightItem[] = []

  if (sig === 'monolith_growth') {
    const gods = r.graph?.god_modules ?? []
    if (gods.length) {
      for (const g of gods.slice(0, 6)) {
        items.push({ text: g.module, sub: `imported by ${g.in_degree} file${g.in_degree !== 1 ? 's' : ''}`, highlight: g.in_degree >= 10, monospace: true })
      }
      if (gods.length > 6) items.push({ text: `…and ${gods.length - 6} more` })
    }
    const cycles = r.graph?.cycles ?? []
    if (cycles.length) {
      const ex = cycles[0]
      if (ex.length >= 2) {
        items.push({ text: ex.slice(0, 3).join(' → ') + (ex.length > 3 ? ' → …' : ''), sub: 'example cycle', monospace: true })
      }
    }
  }

  if (sig === 'dependency_health') {
    const dockerIssues = r.dependencies?.docker_issues ?? []
    for (const d of dockerIssues.slice(0, 4)) {
      items.push({ text: d.file, sub: d.issue, highlight: true, monospace: true })
    }
    const lockfiles = r.dependencies?.missing_lockfile_warnings ?? []
    for (const l of lockfiles.slice(0, 4)) {
      items.push({ text: l, sub: 'missing lockfile', highlight: true })
    }
    const depCount = r.dependencies?.dependency_count ?? 0
    items.push({ text: `${depCount.toLocaleString()} total dependencies` })
  }

  if (sig === 'documentation_quality') {
    const readme = r.readme
    if (!readme?.found) {
      items.push({ text: 'No README detected', highlight: true })
    } else {
      items.push({ text: `README: ${readme.word_count.toLocaleString()} words`, highlight: readme.word_count < 100 })
      if (!readme.has_installation) items.push({ text: 'Missing installation instructions', highlight: true })
      if (!readme.has_usage) items.push({ text: 'Missing usage section', highlight: true })
      if (!readme.has_changelog) items.push({ text: 'Changelog not referenced in README' })
      if (!readme.has_contributing) items.push({ text: 'Contributing guide not in README' })
      if (!r.structure?.has_contributing) items.push({ text: 'No CONTRIBUTING.md file', highlight: true })
    }
  }

  if (sig === 'ci_health') {
    const s = r.structure
    if (s) {
      if (s.has_ci) {
        items.push({ text: s.ci_systems.join(', '), sub: `CI system${s.ci_systems.length > 1 ? 's' : ''} detected` })
        if (s.gh_workflow_count > 0) {
          items.push({ text: `${s.gh_workflow_count} GitHub workflow${s.gh_workflow_count !== 1 ? 's' : ''}` })
        }
      } else {
        items.push({ text: 'No CI configuration detected', highlight: true })
      }
      const testPct = (s.test_ratio * 100).toFixed(1)
      items.push({ text: `Test file ratio: ${testPct}%`, highlight: s.test_ratio < 0.05, sub: s.test_ratio < 0.05 ? 'very few test files' : s.test_ratio < 0.15 ? 'below average' : undefined })
      items.push({ text: s.has_lint_config ? 'Linting configured' : 'No lint config detected', highlight: !s.has_lint_config })
    }
  }

  if (sig === 'bus_factor_risk') {
    const busFactor = r.structure?.bus_factor ?? r.ownership?.bus_factor ?? 0
    items.push({ text: `Bus factor: ${busFactor}`, sub: busFactor <= 1 ? '1 person holds 80%+ of file knowledge' : busFactor <= 2 ? '2 people hold 80%+ of file knowledge' : `${busFactor} contributors needed to cover 80% of the codebase`, highlight: busFactor <= 2 })
    const topContribs = r.structure?.top_contributors ?? r.ownership?.top_contributors ?? []
    for (const c of topContribs.slice(0, 5)) {
      items.push({ text: c.author, sub: `${c.files_touched.toLocaleString()} file${c.files_touched !== 1 ? 's' : ''} touched` })
    }
  }

  if (sig === 'security_hygiene') {
    const sec = r.security
    if (sec) {
      if (!sec.gitignore_exists) {
        items.push({ text: 'No .gitignore file', highlight: true })
      } else if (sec.gitignore_gaps.length) {
        items.push({ text: `Missing patterns: ${sec.gitignore_gaps.slice(0, 5).join(', ')}`, sub: '.gitignore gaps', monospace: true })
      } else {
        items.push({ text: '.gitignore present with no detected gaps' })
      }
      const vulns = sec.vulnerabilities ?? []
      if (vulns.length) {
        for (const v of vulns.slice(0, 4)) {
          items.push({ text: `${v.name}@${v.version}`, sub: `${v.vuln_id}${v.severity ? ` · ${v.severity}` : ''}`, highlight: true, monospace: true })
        }
        if (vulns.length > 4) items.push({ text: `…and ${vulns.length - 4} more CVE${vulns.length - 4 > 1 ? 's' : ''}` })
      }
    }
  }

  if (sig === 'release_cadence') {
    const s = r.structure
    if (s) {
      items.push({ text: `${s.release_count} total release${s.release_count !== 1 ? 's' : ''}`, highlight: s.release_count === 0 })
      if (s.last_release) {
        const d = new Date(s.last_release.date)
        const days = Math.floor((Date.now() - d.getTime()) / 86400000)
        items.push({ text: s.last_release.name, sub: `${days} days ago · ${d.toLocaleDateString()}`, highlight: days > 365, monospace: true })
      }
    }
  }

  if (sig === 'community_health') {
    const s = r.structure
    if (s) {
      const checks = isClosedSource.value
        ? [
            { label: 'SECURITY policy', present: s.has_security_policy, file: s.security_policy_file, critical: false },
          ]
        : [
            { label: 'License', present: !!(s.license_type || s.license_file), file: s.license_file ?? (s.license_type ? `(${s.license_type})` : null), critical: true },
            { label: 'CONTRIBUTING', present: s.has_contributing, file: s.contributing_file, critical: false },
            { label: 'SECURITY policy', present: s.has_security_policy, file: s.security_policy_file, critical: false },
            { label: 'Code of Conduct', present: s.has_coc, file: s.coc_file, critical: false },
            { label: 'CHANGELOG', present: s.has_changelog, file: s.changelog_file, critical: false },
          ]
      for (const c of checks) {
        items.push({
          text: c.present ? `✓ ${c.label}${c.file ? ` — ${c.file}` : ''}` : `✗ ${c.label}`,
          highlight: !c.present && c.critical,
        })
      }
    }
  }

  if (sig === 'burnout') {
    const commits = r.commits
    items.push({ text: `Activity at ${(commits.activity_decay_ratio * 100).toFixed(0)}% of historical pace`, highlight: commits.activity_decay_ratio < 0.5 })
    const churn = commits.contributor_churn
    if (churn.length >= 2) {
      const peak = Math.max(...churn.map(c => c.active))
      const recent = churn[churn.length - 1].active
      const pct = peak > 0 ? ((recent / peak) * 100).toFixed(0) : '100'
      items.push({ text: `${recent} active contributor${recent !== 1 ? 's' : ''} now`, sub: `down from peak of ${peak} (${pct}% retained)`, highlight: recent < peak * 0.5 })
    }
  }

  if (sig === 'abandonment_risk') {
    const days = r.commits.days_since_last_commit
    const lastDate = r.commits.last_commit_date
    if (days != null) {
      items.push({ text: `${days} day${days !== 1 ? 's' : ''} since last commit`, highlight: days > 180 })
    }
    if (lastDate) {
      items.push({ text: new Date(lastDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }), sub: 'last commit date' })
    }
  }

  if (sig === 'commit_velocity') {
    const monthly = r.commits.monthly_frequency
    if (monthly.length >= 6) {
      const recent = monthly.slice(-3)
      const prior = monthly.slice(-6, -3)
      const recentAvg = recent.reduce((s, m) => s + m.count, 0) / 3
      const priorAvg = prior.reduce((s, m) => s + m.count, 0) / 3
      items.push({ text: `${recentAvg.toFixed(1)} commits/month`, sub: 'recent 3-month average', highlight: recentAvg < priorAvg * 0.5 })
      items.push({ text: `${priorAvg.toFixed(1)} commits/month`, sub: 'prior 3-month average' })
      if (priorAvg > 0) {
        const ratio = ((recentAvg / priorAvg) * 100).toFixed(0)
        items.push({ text: `${ratio}% of prior pace` })
      }
    }
  }

  if (sig === 'license_risk') {
    const lic = r.structure?.license_type ?? r.structure?.license_file
    if (!lic) {
      if (isClosedSource.value) {
        items.push({ text: 'No license file — not required for closed-source context' })
      } else {
        items.push({ text: 'No license file detected', highlight: true, sub: 'legally all-rights-reserved without one' })
      }
    } else {
      items.push({ text: lic, sub: 'detected license' })
    }
  }

  if (sig === 'complexity_debt') {
    const hotspots = (r as any)?.complexity?.hotspots ?? []
    const threshold = (r as any)?.complexity?.threshold ?? 500
    if (hotspots.length) {
      for (const h of hotspots.slice(0, 5)) {
        const noTest = !h.has_adjacent_test
        items.push({ text: h.path ?? h.file ?? 'unknown', sub: `${h.lines ?? h.loc ?? '?'} lines${noTest ? ' · no adjacent tests' : ''}`, highlight: noTest, monospace: true })
      }
      if (hotspots.length > 5) items.push({ text: `…and ${hotspots.length - 5} more` })
    } else {
      items.push({ text: `No files exceed ${threshold} LOC` })
    }
  }

  if (sig === 'test_coverage') {
    const tc = (r as any)?.test_coverage
    if (tc) {
      const ratio = tc.test_ratio ?? 0
      items.push({ text: `${(ratio * 100).toFixed(1)}% test file ratio`, highlight: ratio < 0.05 })
      if (tc.framework_detected) items.push({ text: tc.framework_detected, sub: 'test framework detected' })
      const untested = tc.untested_dirs ?? []
      for (const d of untested.slice(0, 5)) {
        items.push({ text: d, sub: 'no test files', highlight: true, monospace: true })
      }
      if (untested.length > 5) items.push({ text: `…and ${untested.length - 5} more untested directories` })
    }
  }

  if (sig === 'cicd_maturity') {
    const cicd = (r as any)?.cicd
    if (cicd) {
      items.push({ text: cicd.system ?? 'CI detected', sub: cicd.workflow_count ? `${cicd.workflow_count} workflow${cicd.workflow_count !== 1 ? 's' : ''}` : 'no workflows' })
      const s = cicd.summary ?? {}
      items.push({ text: s.has_tests ? '✓ Test step in CI' : '✗ No test step in CI', highlight: !s.has_tests })
      items.push({ text: s.has_lint ? '✓ Lint step in CI' : '✗ No lint step in CI', highlight: !s.has_lint })
      if (s.has_deploy != null) items.push({ text: s.has_deploy ? '✓ Deploy step present' : '✗ No deploy step' })
    }
  }

  if (sig === 'container_hygiene') {
    const cont = (r as any)?.container
    if (cont) {
      const dockerfiles = cont.dockerfiles ?? []
      for (const d of dockerfiles.slice(0, 4)) {
        const rootFlag = d.runs_as_root ? ' · runs as root' : ''
        items.push({ text: d.path ?? 'Dockerfile', sub: `${(d.issues ?? []).length} issue${(d.issues ?? []).length !== 1 ? 's' : ''}${rootFlag}`, highlight: d.runs_as_root, monospace: true })
        for (const issue of (d.issues ?? []).filter((i: any) => i.severity === 'high').slice(0, 2)) {
          items.push({ text: issue.message ?? issue.code ?? 'high-severity issue', highlight: true })
        }
      }
    }
  }

  return items.length > 0 ? items : null
})

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="signal && info" class="h-drawer-root">
        <div class="h-drawer-backdrop" @click="emit('close')" />
        <div class="h-drawer" role="dialog" aria-modal="true">
          <div class="h-drawer__header">
            <div class="h-drawer__header-left">
              <span class="h-drawer__icon">{{ ICONS[signal.signal] }}</span>
              <span class="h-drawer__title">{{ signal.label }}</span>
            </div>
            <button class="h-drawer__close" @click="emit('close')" aria-label="Close">✕</button>
          </div>

          <div class="h-drawer__body">
            <!-- Live score -->
            <div :class="['h-drawer__score-bar-wrap', `h-drawer__score-bar-wrap--${level(signal.score)}`]">
              <div class="h-drawer__score-row">
                <span :class="['h-drawer__score-num', `h-drawer__score-num--${level(signal.score)}`]">
                  {{ signal.score }}
                </span>
                <span class="h-drawer__score-denom">/ 100</span>
                <span :class="['h-drawer__risk-badge', `h-drawer__risk-badge--${level(signal.score)}`]">
                  {{ riskLabel(signal.score) }}
                </span>
              </div>
              <div class="h-drawer__bar">
                <div
                  :class="['h-drawer__bar-fill', `h-drawer__bar-fill--${level(signal.score)}`]"
                  :style="{ width: `${signal.score}%` }"
                />
              </div>
              <p class="h-drawer__live-desc">{{ signal.description }}</p>
            </div>

            <!-- In this repo -->
            <template v-if="repoInsight">
              <hr class="h-drawer__divider" />
              <section class="h-drawer__section">
                <h3 class="h-drawer__section-title">In this repo</h3>
                <ul class="h-drawer__repo-list">
                  <li
                    v-for="(item, i) in repoInsight"
                    :key="i"
                    :class="['h-drawer__repo-item', item.highlight && 'h-drawer__repo-item--highlight']"
                  >
                    <span :class="['h-drawer__repo-item-text', item.monospace && 'h-drawer__repo-item-text--mono']">{{ item.text }}</span>
                    <span v-if="item.sub" class="h-drawer__repo-item-sub">{{ item.sub }}</span>
                  </li>
                </ul>
              </section>
            </template>

            <hr class="h-drawer__divider" />

            <!-- Overview -->
            <section class="h-drawer__section">
              <h3 class="h-drawer__section-title">Overview</h3>
              <p class="h-drawer__section-body h-drawer__section-body--overview">{{ info.overview }}</p>
            </section>

            <!-- Findings (only when present) -->
            <template v-if="signal.items?.length">
              <hr class="h-drawer__divider" />
              <section class="h-drawer__section">
                <h3 class="h-drawer__section-title h-drawer__section-title--findings">Findings</h3>
                <ul class="h-drawer__findings-list">
                  <li v-for="(item, i) in signal.items" :key="i">{{ item }}</li>
                </ul>
              </section>
            </template>

            <hr class="h-drawer__divider" />

            <!-- What raises the score -->
            <section class="h-drawer__section">
              <h3 class="h-drawer__section-title">What raises this score</h3>
              <ul class="h-drawer__list">
                <li v-for="(r, i) in info.raises" :key="i"><strong>{{ r.split(' — ')[0] }}</strong><template v-if="r.includes(' — ')"> — {{ r.split(' — ')[1] }}</template></li>
              </ul>
            </section>

            <hr class="h-drawer__divider" />

            <!-- Guidance -->
            <section class="h-drawer__section">
              <h3 class="h-drawer__section-title">What to look for</h3>
              <p class="h-drawer__section-body"><em>{{ info.guidance }}</em></p>
            </section>

            <!-- Confidence -->
            <div class="h-drawer__confidence">
              <span :class="['heuristic__confidence-dot', `heuristic__confidence-dot--${signal.confidence}`]" />
              <span class="h-drawer__confidence-text"><strong>{{ signal.confidence }}</strong> confidence signal</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
