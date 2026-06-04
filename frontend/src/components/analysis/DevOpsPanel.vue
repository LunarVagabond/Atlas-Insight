<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { CicdData, ContainerData, ChangelogData } from '../../stores/analysis'

const props = defineProps<{
  cicd?: CicdData
  containers?: ContainerData
  changelog?: ChangelogData
}>()

function severityVariant(s: string): 'failed' | 'warning' | 'info' {
  if (s === 'high') return 'failed'
  if (s === 'medium') return 'warning'
  return 'info'
}

function ciScoreLabel(score: number): string {
  if (score >= 80) return 'Mature'
  if (score >= 60) return 'Adequate'
  if (score >= 40) return 'Basic'
  if (score > 0) return 'Minimal'
  return 'None'
}

function ciScoreBadge(score: number): 'info' | 'warning' | 'failed' {
  if (score >= 60) return 'info'
  if (score >= 40) return 'warning'
  return 'failed'
}

const changelogFormatLabel: Record<string, string> = {
  'keep-a-changelog': 'Keep a Changelog (standard format)',
  versioned: 'Versioned',
  prose: 'Prose',
  none: 'None',
}

const allContainerIssues = computed(() => {
  const dfs = props.containers?.dockerfiles ?? []
  return dfs.flatMap(df =>
    df.issues.map(i => ({ ...i, path: df.path }))
  )
})
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">DevOps</h2>
    <p class="panel__subtitle">CI/CD pipeline depth, container hygiene from Dockerfile static analysis, and changelog discipline. All static — no runtime checks.</p>

    <!-- ── CI/CD ──────────────────────────────────────────────── -->
    <section class="devops-section">
      <h3 class="devops-section__title">CI/CD Pipeline</h3>

      <div class="panel__grid panel__grid--2col" style="margin-bottom: 1rem">
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">
              <AppBadge :variant="ciScoreBadge(cicd?.score ?? 0)" style="font-size: 1rem">
                {{ ciScoreLabel(cicd?.score ?? 0) }}
              </AppBadge>
            </div>
            <div class="stat__label" style="margin-top: 0.5rem">
              Maturity · {{ cicd?.score ?? 0 }}/100
              <span v-if="cicd?.system" class="devops-system-tag"> via {{ cicd.system.replace(/_/g, ' ') }}</span>
            </div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="devops-ci-checklist">
            <div class="devops-ci-check" :class="cicd?.summary?.has_tests ? 'devops-ci-check--ok' : 'devops-ci-check--miss'">
              {{ cicd?.summary?.has_tests ? '✓' : '✗' }} Tests
            </div>
            <div class="devops-ci-check" :class="cicd?.summary?.has_lint ? 'devops-ci-check--ok' : 'devops-ci-check--miss'">
              {{ cicd?.summary?.has_lint ? '✓' : '✗' }} Lint
            </div>
            <div class="devops-ci-check" :class="cicd?.summary?.has_deploy ? 'devops-ci-check--ok' : 'devops-ci-check--miss'">
              {{ cicd?.summary?.has_deploy ? '✓' : '✗' }} Deploy
            </div>
            <div class="devops-ci-check" :class="cicd?.summary?.has_matrix ? 'devops-ci-check--ok' : 'devops-ci-check--miss'">
              {{ cicd?.summary?.has_matrix ? '✓' : '✗' }} Matrix
            </div>
          </div>
        </AppCard>
      </div>

      <div v-if="(cicd?.workflows?.length ?? 0) > 0">
        <table class="data-table">
          <thead>
            <tr>
              <th>Workflow</th>
              <th>Triggers</th>
              <th>Jobs</th>
              <th>Tests</th>
              <th>Lint</th>
              <th>Deploy</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="wf in cicd?.workflows" :key="wf.name">
              <td>{{ wf.name }}</td>
              <td class="devops-triggers">{{ wf.triggers.join(', ') || '—' }}</td>
              <td>{{ wf.job_count || '—' }}</td>
              <td><AppBadge :variant="wf.has_tests ? 'info' : 'warning'">{{ wf.has_tests ? 'Yes' : 'No' }}</AppBadge></td>
              <td><AppBadge :variant="wf.has_lint ? 'info' : 'warning'">{{ wf.has_lint ? 'Yes' : 'No' }}</AppBadge></td>
              <td><AppBadge :variant="wf.has_deploy ? 'info' : 'info'">{{ wf.has_deploy ? 'Yes' : 'No' }}</AppBadge></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="panel__hint">No CI/CD configuration detected.</div>
    </section>

    <!-- ── Container hygiene ──────────────────────────────────── -->
    <section class="devops-section">
      <h3 class="devops-section__title">Container Hygiene</h3>

      <div v-if="(containers?.dockerfile_count ?? 0) === 0" class="panel__hint">
        No Dockerfiles found in this repository.
      </div>

      <template v-else>
        <div class="panel__grid" style="margin-bottom: 1rem">
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value">{{ containers?.dockerfile_count }}</div>
              <div class="stat__label">Dockerfiles</div>
            </div>
          </AppCard>
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value" :class="(containers?.total_issues ?? 0) > 0 ? 'stat__value--warn' : 'stat__value--ok'">
                {{ containers?.total_issues ?? 0 }}
              </div>
              <div class="stat__label">Issues Found</div>
            </div>
          </AppCard>
          <AppCard elevated>
            <div class="stat">
              <div class="stat__value">
                {{ containers?.dockerfiles?.filter(d => d.is_multistage).length ?? 0 }}
              </div>
              <div class="stat__label">Multi-stage Builds</div>
            </div>
          </AppCard>
        </div>

        <table v-if="allContainerIssues.length > 0" class="data-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Severity</th>
              <th>Line</th>
              <th>Issue</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(issue, i) in allContainerIssues.slice(0, 30)" :key="i">
              <td class="mono devops-truncate">{{ issue.path }}</td>
              <td><AppBadge :variant="severityVariant(issue.severity)">{{ issue.severity }}</AppBadge></td>
              <td>{{ issue.line ?? '—' }}</td>
              <td>{{ issue.message }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="panel__hint">No Dockerfile issues detected.</div>
      </template>
    </section>

    <!-- ── Changelog discipline ───────────────────────────────── -->
    <section class="devops-section">
      <h3 class="devops-section__title">Changelog Discipline</h3>
      <p class="panel__hint" style="margin: 0 0 0.75rem 0">
        Checks whether a changelog exists, what style it uses, and whether it appears stale. “Keep a Changelog” is a detected format label, not a hard requirement.
      </p>

      <div class="panel__grid panel__grid--2col" style="margin-bottom: 1rem">
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">
              <AppBadge :variant="changelog?.found ? 'info' : 'failed'">
                {{ changelog?.found ? 'Present' : 'Missing' }}
              </AppBadge>
            </div>
            <div class="stat__label" style="margin-top: 0.5rem">Changelog</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ changelogFormatLabel[changelog?.format ?? 'none'] }}</div>
            <div class="stat__label">Format</div>
          </div>
        </AppCard>
      </div>

      <div v-if="changelog?.found" class="panel__grid" style="margin-bottom: 1rem">
        <AppCard>
          <div class="stat">
            <div class="stat__value">{{ changelog?.entry_count ?? 0 }}</div>
            <div class="stat__label">Version Entries</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="stat">
            <div class="stat__value">{{ changelog?.last_entry_version ?? '—' }}</div>
            <div class="stat__label">Last Version</div>
          </div>
        </AppCard>
        <AppCard>
          <div class="stat">
            <div class="stat__value">{{ changelog?.days_stale != null ? changelog.days_stale + 'd' : '—' }}</div>
            <div class="stat__label">Days Since Update</div>
          </div>
        </AppCard>
      </div>

      <div v-if="(changelog?.issues?.length ?? 0) > 0" style="margin-top: 0.75rem">
        <table class="data-table">
          <thead>
            <tr><th>Severity</th><th>Issue</th></tr>
          </thead>
          <tbody>
            <tr v-for="(issue, i) in changelog?.issues" :key="i">
              <td><AppBadge :variant="severityVariant(issue.severity)">{{ issue.severity }}</AppBadge></td>
              <td>{{ issue.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="changelog?.found" class="panel__hint">Changelog is up to date with no detected issues.</div>
    </section>
  </div>
</template>
