<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import AppTabs from '../ui/AppTabs.vue'
import type { CicdData, ContainerData, ChangelogData, TerraformData, ToolsData } from '../../stores/analysis'

const props = defineProps<{
  cicd?: CicdData
  containers?: ContainerData
  changelog?: ChangelogData
  tools?: ToolsData
  section?: string
}>()

const emit = defineEmits<{ 'update:section': [section: string] }>()

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

const terraform = computed<TerraformData | undefined>(() => props.tools?.terraform as TerraformData | undefined)

const topResourceTypes = computed(() => {
  const types = terraform.value?.resource_types ?? {}
  return Object.entries(types)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
})

function tfScoreLabel(score: number): string {
  if (score >= 80) return 'Well-configured'
  if (score >= 60) return 'Adequate'
  if (score >= 40) return 'Basic'
  if (score > 0) return 'Minimal'
  return 'Unconfigured'
}

function tfScoreBadge(score: number): 'info' | 'warning' | 'failed' {
  if (score >= 60) return 'info'
  if (score >= 40) return 'warning'
  return 'failed'
}

const visibleSections = computed(() => {
  const sections: string[] = ['CI/CD']
  if ((props.containers?.dockerfile_count ?? 0) > 0) sections.push('Containers')
  if (props.changelog?.found || (props.changelog?.issues?.length ?? 0) > 0) sections.push('Changelog')
  sections.push('Infrastructure')
  return sections
})

const activeSection = computed(() => {
  const visible = visibleSections.value
  if (props.section && visible.includes(props.section)) return props.section
  return visible[0]
})
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">DevOps</h2>
    <p class="panel__subtitle">CI/CD pipeline depth, container hygiene from Dockerfile static analysis, and changelog discipline. All static — no runtime checks.</p>

    <div class="panel__sub-tabs">
      <AppTabs
        :tabs="visibleSections"
        :model-value="activeSection"
        @update:model-value="emit('update:section', $event)"
      />
    </div>

    <!-- ── CI/CD ──────────────────────────────────────────────── -->
    <section v-if="activeSection === 'CI/CD'" class="devops-section">
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
    <section v-else-if="activeSection === 'Containers'" class="devops-section">
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
    <section v-else-if="activeSection === 'Changelog'" class="devops-section">
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

    <!-- ── Infrastructure ─────────────────────────────────────── -->
    <section v-else-if="activeSection === 'Infrastructure'" class="devops-section">
      <template v-if="!terraform">
        <div class="devops-infra-hint">
          <p>No supported infrastructure tooling detected in this repository.</p>
          <p>Atlas Insight analyses <strong>Docker</strong> and <strong>Terraform</strong> configurations — detecting providers, resource counts, hygiene scores, and common security issues. These sections appear automatically when the tool is detected.</p>
          <p class="devops-infra-hint__links">
            Supported tooling: <a href="/supported#tools" target="_blank">What's Supported</a>
            · <a href="/docs/dev/adding-a-tool" target="_blank">Adding a tool</a>
          </p>
        </div>
      </template>

      <template v-else>
      <h3 class="devops-section__title">Terraform</h3>

      <div class="panel__grid panel__grid--2col" style="margin-bottom: 1rem">
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">
              <AppBadge :variant="tfScoreBadge(terraform.score)" style="font-size: 1rem">
                {{ tfScoreLabel(terraform.score) }}
              </AppBadge>
            </div>
            <div class="stat__label" style="margin-top: 0.5rem">Hygiene · {{ terraform.score }}/100</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ terraform.file_count }}</div>
            <div class="stat__label">.tf Files</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ terraform.resource_count }}</div>
            <div class="stat__label">Resources</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value">{{ terraform.backend ?? 'local' }}</div>
            <div class="stat__label">State Backend</div>
          </div>
        </AppCard>
      </div>

      <div v-if="terraform.providers.length > 0" class="devops-tf-providers" style="margin-bottom: 1rem">
        <span class="devops-tf-label">Providers</span>
        <AppBadge v-for="p in terraform.providers" :key="p" variant="info" style="margin-right: 0.25rem">{{ p }}</AppBadge>
      </div>

      <div v-if="terraform.version_constraint" class="devops-tf-meta" style="margin-bottom: 1rem">
        <span class="devops-tf-label">Required version</span>
        <code class="mono">{{ terraform.version_constraint }}</code>
      </div>

      <div v-if="topResourceTypes.length > 0" style="margin-bottom: 1rem">
        <table class="data-table">
          <thead>
            <tr><th>Resource Type</th><th>Count</th></tr>
          </thead>
          <tbody>
            <tr v-for="([type, count]) in topResourceTypes" :key="type">
              <td class="mono">{{ type }}</td>
              <td>{{ count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="terraform.security_issues.length > 0" style="margin-top: 0.75rem">
        <table class="data-table">
          <thead>
            <tr><th>Resource</th><th>Severity</th><th>Issue</th></tr>
          </thead>
          <tbody>
            <tr v-for="(issue, i) in terraform.security_issues" :key="i">
              <td class="mono devops-truncate">{{ issue.resource }}</td>
              <td><AppBadge :variant="severityVariant(issue.severity)">{{ issue.severity }}</AppBadge></td>
              <td>{{ issue.issue }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="panel__hint">No Terraform security issues detected.</div>
      </template>
    </section>
  </div>
</template>
