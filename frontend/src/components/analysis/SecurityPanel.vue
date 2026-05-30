<script setup lang="ts">
import { computed, ref } from 'vue'
import AppCard from '../ui/AppCard.vue'
import HeuristicDrawer from './HeuristicDrawer.vue'
import type { HeuristicSignal, SecurityData, StructureData } from '../../stores/analysis'

const props = defineProps<{
  security?: SecurityData
  heuristics?: HeuristicSignal[]
  structure?: StructureData
}>()

const securitySignal = computed(() =>
  props.heuristics?.find(s => s.signal === 'security_hygiene') ?? null
)

const active = ref<HeuristicSignal | null>(null)

function level(score: number): 'low' | 'medium' | 'high' {
  if (score < 30) return 'low'
  if (score < 60) return 'medium'
  return 'high'
}

function riskLabel(score: number): string {
  if (score < 30) return 'Low Risk'
  if (score < 60) return 'Moderate Risk'
  return 'High Risk'
}

const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
const sortedIssues = computed(() =>
  [...(props.security?.issues ?? [])].sort(
    (a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9)
  )
)
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Security</h2>

    <!-- Heuristic signal card -->
    <div v-if="securitySignal" class="security-panel__signal-row">
      <AppCard
        elevated
        :class="['heuristic-card', `heuristic-card--${level(securitySignal.score)}`, 'heuristic-card--clickable']"
        @click="active = securitySignal"
      >
        <div class="heuristic">
          <div class="heuristic__top">
            <div class="heuristic__title-group">
              <div class="heuristic__icon-label">
                <span class="heuristic__icon">🔒</span>
                <span class="heuristic__label">{{ securitySignal.label }}</span>
              </div>
              <span :class="['heuristic__risk', `heuristic__risk--${level(securitySignal.score)}`]">
                {{ riskLabel(securitySignal.score) }}
              </span>
            </div>
            <div class="heuristic__score-display">
              <span :class="['heuristic__score-number', `heuristic__score-number--${level(securitySignal.score)}`]">
                {{ securitySignal.score }}
              </span>
              <span class="heuristic__score-label">/ 100</span>
            </div>
          </div>
          <div class="heuristic__bar">
            <div
              :class="['heuristic__bar-fill', `heuristic__bar-fill--${level(securitySignal.score)}`]"
              :style="{ width: `${securitySignal.score}%` }"
            />
          </div>
          <div class="heuristic__footer">
            <span :class="['heuristic__confidence-dot', `heuristic__confidence-dot--${securitySignal.confidence}`]" />
            <span class="heuristic__confidence-text">{{ securitySignal.confidence }} confidence</span>
            <span class="heuristic__details-hint">Details →</span>
          </div>
        </div>
      </AppCard>
    </div>

    <!-- Policy & gitignore status -->
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

    <!-- Scan issues table -->
    <div v-if="sortedIssues.length" class="security-panel__issues">
      <h3 class="panel__subtitle">Scan Findings <span class="badge">{{ sortedIssues.length }}</span></h3>
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
    <div v-else class="security-panel__clear">
      <span>✓</span> No scan findings detected.
    </div>

    <HeuristicDrawer :signal="active" @close="active = null" />
  </div>
</template>
