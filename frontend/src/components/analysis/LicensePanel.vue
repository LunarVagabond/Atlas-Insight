<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { LicenseData } from '../../stores/analysis'

const props = defineProps<{
  license?: LicenseData
}>()

const hasData = computed(() => !!props.license && props.license.source !== undefined)

function severityVariant(s: string): 'failed' | 'warning' | 'info' {
  if (s === 'high') return 'failed'
  if (s === 'medium') return 'warning'
  return 'info'
}

const compatibleDeps = computed(() => (props.license?.dep_licenses ?? []).filter(d => d.compatible === true))
const incompatibleDeps = computed(() => (props.license?.dep_licenses ?? []).filter(d => d.compatible === false))
const unknownDeps = computed(() => (props.license?.dep_licenses ?? []).filter(d => d.compatible === null))
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">License</h2>
    <p class="panel__subtitle">Detected project license, OSI approval status, and compatibility check against known dependency licenses. Uses static lookup — does not query external APIs.</p>

    <div v-if="!hasData" class="panel__hint">No license analysis data available for this repository.</div>

    <template v-else>
      <!-- Project license summary -->
      <div class="panel__grid panel__grid--2col" style="margin-bottom: var(--space-6)">
        <AppCard elevated>
          <div class="stat">
            <div class="stat__value" style="font-size: 1.4rem">
              {{ license?.spdx_id ?? 'None' }}
            </div>
            <div class="stat__label">SPDX Identifier</div>
          </div>
        </AppCard>
        <AppCard elevated>
          <div class="license-panel__badges">
            <div class="stat__label" style="margin-bottom: var(--space-2)">Properties</div>
            <AppBadge v-if="license?.osi_approved" variant="info">OSI Approved</AppBadge>
            <AppBadge v-if="license?.copyleft" variant="warning">Copyleft</AppBadge>
            <AppBadge v-if="!license?.osi_approved && license?.source !== 'none'" variant="info">Non-OSI</AppBadge>
            <AppBadge v-if="license?.source === 'none'" variant="failed">No License</AppBadge>
            <span v-if="license?.source === 'file'" class="license-panel__source">from {{ license.source_file }}</span>
            <span v-else-if="license?.source === 'github_api'" class="license-panel__source">from GitHub API</span>
          </div>
        </AppCard>
      </div>

      <!-- Issues -->
      <div v-if="(license?.issues?.length ?? 0) > 0" style="margin-bottom: var(--space-6)">
        <h3 class="license-panel__section-title">Issues</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(issue, i) in license?.issues" :key="i">
              <td><AppBadge :variant="severityVariant(issue.severity)">{{ issue.severity }}</AppBadge></td>
              <td>{{ issue.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Dependency licenses -->
      <div v-if="(license?.dep_licenses?.length ?? 0) > 0">
        <h3 class="license-panel__section-title">
          Dependency License Compatibility
          <span class="license-panel__sub">({{ license?.dep_licenses?.length }} deps checked)</span>
        </h3>

        <div class="panel__grid" style="margin-bottom: var(--space-4)">
          <AppCard>
            <div class="stat">
              <div class="stat__value stat__value--ok">{{ compatibleDeps.length }}</div>
              <div class="stat__label">Compatible</div>
            </div>
          </AppCard>
          <AppCard>
            <div class="stat">
              <div class="stat__value" :class="incompatibleDeps.length ? 'stat__value--warn' : 'stat__value--ok'">
                {{ incompatibleDeps.length }}
              </div>
              <div class="stat__label">Incompatible</div>
            </div>
          </AppCard>
          <AppCard>
            <div class="stat">
              <div class="stat__value">{{ unknownDeps.length }}</div>
              <div class="stat__label">Unknown</div>
            </div>
          </AppCard>
        </div>

        <table v-if="incompatibleDeps.length > 0" class="data-table">
          <thead>
            <tr>
              <th>Package</th>
              <th>License</th>
              <th>Compatibility</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="dep in incompatibleDeps" :key="dep.name">
              <td class="mono">{{ dep.name }}</td>
              <td>{{ dep.license ?? '—' }}</td>
              <td><AppBadge variant="failed">Incompatible</AppBadge></td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="!license?.spdx_id && license?.source === 'none'" class="panel__disclaimer">
        Without a license, all rights are reserved by default under copyright law. Contributors and users cannot legally use, modify, or distribute the code.
      </p>
    </template>
  </div>
</template>
