<script setup lang="ts">
import { computed } from 'vue'
import AppBadge from '../ui/AppBadge.vue'
import AppTabs from '../ui/AppTabs.vue'
import type { SecurityData, StructureData } from '../../stores/analysis'

const SECTIONS = ['Patterns', 'CVEs'] as const

const props = defineProps<{
  security?: SecurityData
  structure?: StructureData
  section?: string
}>()

const emit = defineEmits<{ 'update:section': [section: string] }>()

const activeSection = computed(() =>
  props.section && SECTIONS.includes(props.section as typeof SECTIONS[number])
    ? props.section
    : 'Patterns',
)

const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
const sortedIssues = computed(() =>
  [...(props.security?.issues ?? [])].sort(
    (a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9)
  )
)

const vulns = computed(() => props.security?.vulnerabilities ?? [])

const sectionBadges = computed(() => {
  const badges: Record<string, number | string> = {}
  if (vulns.value.length > 0) badges.CVEs = vulns.value.length
  return badges
})

function vulnSeverityVariant(sev: string | null): 'failed' | 'warning' | 'info' {
  if (!sev) return 'info'
  const s = sev.toLowerCase()
  if (s.includes('critical') || s.includes('high') || s.includes('9.') || s.includes('10.')) return 'failed'
  if (s.includes('medium') || s.includes('moderate')) return 'warning'
  return 'info'
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Security</h2>
    <p class="panel__subtitle">Automated pattern matching — not a full security audit. These highlight areas worth reviewing, not confirmed vulnerabilities. Always consult a security professional for production systems.</p>

    <div class="panel__sub-tabs">
      <AppTabs
        :tabs="[...SECTIONS]"
        :model-value="activeSection"
        :badges="sectionBadges"
        @update:model-value="emit('update:section', $event)"
      />
    </div>

    <template v-if="activeSection === 'Patterns'">
      <p class="panel__hint" style="margin-bottom: 1rem">
        Security hygiene score lives on the <strong>Heuristics</strong> tab under the Security Hygiene signal.
      </p>

      <div class="security-panel__meta">
        <div class="security-panel__meta-item">
          <span :class="['security-panel__status-dot', structure?.has_security_policy ? 'security-panel__status-dot--ok' : 'security-panel__status-dot--missing']" />
          <span>Security Policy</span>
          <span class="security-panel__status-label">
            {{ structure?.has_security_policy ? (structure.security_policy_file ?? 'Present') : 'Not found' }}
          </span>
        </div>
        <div class="security-panel__meta-item">
          <span :class="['security-panel__status-dot', security?.gitignore_exists ? 'security-panel__status-dot--ok' : 'security-panel__status-dot--missing']" />
          <span>.gitignore</span>
          <span class="security-panel__status-label">
            {{ security?.gitignore_exists ? 'Present' : 'Missing' }}
          </span>
        </div>
        <template v-if="security?.gitignore_gaps?.length">
          <div class="security-panel__meta-item security-panel__meta-item--warn">
            <span>Gitignore gaps:</span>
            <span class="security-panel__gaps">{{ security.gitignore_gaps.join(', ') }}</span>
          </div>
        </template>
      </div>

      <div v-if="sortedIssues.length" class="security-panel__issues">
        <h3 class="panel__subtitle">Patterns detected ({{ sortedIssues.length }}) — review each to decide if action is needed</h3>
        <div class="panel-table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Type</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(issue, i) in sortedIssues" :key="i">
                <td>
                  <span :class="['badge', `badge--${issue.severity}`]">{{ issue.severity }}</span>
                </td>
                <td class="security-panel__type">{{ issue.type }}</td>
                <td class="security-panel__detail">{{ issue.detail }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="security-panel__clear">
        <span>✓</span> No common security patterns detected — this doesn't guarantee the code is secure, but no automated red flags were found.
      </div>
    </template>

    <template v-else-if="activeSection === 'CVEs'">
      <p style="font-size:0.8125rem;color:var(--color-text-muted);margin:0 0 0.75rem">
        Scanned at analysis time against the OSV vulnerability database. Results reflect the version specs found in dependency files — pinned lockfile versions are more accurate.
      </p>

      <div v-if="vulns.length === 0" class="security-panel__clear">
        <span>✓</span> No known CVEs detected in scanned dependencies.
      </div>

      <div v-else class="panel-table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Package</th>
              <th>Version</th>
              <th>CVE ID</th>
              <th>Summary</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in vulns" :key="v.vuln_id + v.name">
              <td><strong>{{ v.name }}</strong></td>
              <td><code>{{ v.version }}</code></td>
              <td>
                <a :href="v.url" target="_blank" rel="noopener noreferrer" class="table-link">{{ v.vuln_id }}</a>
              </td>
              <td>{{ v.summary }}</td>
              <td>
                <AppBadge :variant="vulnSeverityVariant(v.severity)">{{ v.severity ?? 'unknown' }}</AppBadge>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <p class="panel__disclaimer">⚠️ This analysis is based on repository metadata and file patterns only. It does not inspect code for vulnerabilities. A positive score here does not mean the code is secure — never rely on this as a substitute for a proper security audit or penetration test.</p>
  </div>
</template>
