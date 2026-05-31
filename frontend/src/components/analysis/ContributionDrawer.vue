<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import AppBadge from '../ui/AppBadge.vue'
import type { ArchTour, ContributionOpportunity } from '../../stores/analysis'

const props = defineProps<{
  opportunity: ContributionOpportunity | null
  archTours?: ArchTour[]
  repoUrl?: string
}>()
const emit = defineEmits<{ close: [] }>()

const SUBSYSTEM_KEYWORDS: Record<string, string[]> = {
  frontend:  ['ui', 'component', 'page', 'view', 'style', 'css', 'layout', 'render', 'display', 'button', 'form', 'modal'],
  api:       ['api', 'endpoint', 'route', 'handler', 'request', 'response', 'controller', 'auth', 'middleware'],
  data:      ['model', 'schema', 'migration', 'database', 'query', 'db', 'orm', 'table', 'index'],
  tests:     ['test', 'spec', 'coverage', 'assertion', 'mock', 'fixture', 'e2e'],
  config:    ['config', 'ci', 'deploy', 'pipeline', 'workflow', 'docker', 'k8s', 'env'],
  docs:      ['doc', 'readme', 'contributing', 'changelog', 'guide', 'tutorial'],
}

const guidanceTour = computed<ArchTour | null>(() => {
  if (!props.archTours?.length || !props.opportunity) return null
  const isIssue = props.opportunity.category === 'github-issue' || props.opportunity.category === 'feature'
  if (!isIssue) return null
  const text = `${props.opportunity.title} ${props.opportunity.description}`.toLowerCase()
  let bestTour: ArchTour | null = null
  let bestScore = 0
  for (const tour of props.archTours) {
    if (tour.subsystem_type === 'overview') continue
    const keywords = SUBSYSTEM_KEYWORDS[tour.subsystem_type] ?? []
    const score = keywords.filter(kw => text.includes(kw)).length
    if (score > bestScore) {
      bestScore = score
      bestTour = tour
    }
  }
  return bestScore > 0 ? bestTour : null
})

const guidanceSuggestedFiles = computed<string[]>(() => {
  if (!guidanceTour.value) return []
  const files = [
    ...guidanceTour.value.entry_files.slice(0, 2),
    ...guidanceTour.value.reading_order.slice(0, 2).map(s => s.file),
  ]
  return [...new Set(files)].slice(0, 4)
})

function githubFileUrl(file: string): string | null {
  if (!props.repoUrl || !file) return null
  return `${props.repoUrl}/blob/HEAD/${file}`
}

function renderMarkdown(text: string): string {
  const raw = marked.parse(text, { async: false }) as string
  return DOMPurify.sanitize(raw)
}

const CATEGORY_ICONS: Record<ContributionOpportunity['category'], string> = {
  documentation: '📝',
  testing: '🧪',
  ci: '⚙️',
  community: '🤝',
  refactoring: '🔧',
  security: '🔒',
  dependencies: '📦',
  'github-issue': '🐛',
  feature: '✨',
}

const CATEGORY_LABELS: Record<ContributionOpportunity['category'], string> = {
  documentation: 'Documentation',
  testing: 'Testing',
  ci: 'CI/CD',
  community: 'Community',
  refactoring: 'Refactoring',
  security: 'Security',
  dependencies: 'Dependencies',
  'github-issue': 'GitHub Issues',
  feature: 'Feature Requests',
}

function renderHint(hint: string): string {
  return hint.replace(/`([^`]+)`/g, '<code>$1</code>')
}

function diffVariant(d: ContributionOpportunity['difficulty']) {
  return d === 'beginner' ? 'completed' : d === 'intermediate' ? 'warning' : 'failed'
}

function riskVariant(r: ContributionOpportunity['risk']) {
  return r === 'low' ? 'completed' : r === 'medium' ? 'warning' : 'failed'
}

function effortVariant(e: string) {
  if (e === 'quick-win' || e === 'small') return 'completed'
  if (e === 'medium') return 'warning'
  return 'failed'
}

const EFFORT_LABELS: Record<string, string> = {
  'quick-win': 'Quick win (under an hour)',
  'small': 'Small change (a few hours)',
  'medium': 'Medium effort (1–2 days)',
  'large': 'Larger task (multi-day)',
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="contrib-drawer">
      <div v-if="opportunity" class="contrib-drawer-root">
        <div class="contrib-drawer__backdrop" @click="emit('close')" />
        <div class="contrib-drawer__panel" role="dialog" aria-modal="true">
          <div class="contrib-drawer__header">
            <div class="contrib-drawer__header-left">
              <span class="contrib-drawer__icon">{{ CATEGORY_ICONS[opportunity.category] }}</span>
              <span class="contrib-drawer__category-label">{{ CATEGORY_LABELS[opportunity.category] }}</span>
            </div>
            <button class="contrib-drawer__close" @click="emit('close')" aria-label="Close">✕</button>
          </div>

          <div class="contrib-drawer__body">
            <h2 class="contrib-drawer__title">
              <span v-if="opportunity.issue_number" class="contrib-drawer__issue-num">#{{ opportunity.issue_number }}</span>
              {{ opportunity.title }}
            </h2>

            <div class="contrib-drawer__meta">
              <AppBadge :variant="diffVariant(opportunity.difficulty)">{{ opportunity.difficulty }}</AppBadge>
              <AppBadge :variant="riskVariant(opportunity.risk)">{{ opportunity.risk }} risk</AppBadge>
              <AppBadge v-if="opportunity.effort_estimate" :variant="effortVariant(opportunity.effort_estimate)" :title="'Estimated effort for an average developer'">
                {{ EFFORT_LABELS[opportunity.effort_estimate] ?? opportunity.effort_estimate }}
              </AppBadge>
              <template v-if="opportunity.labels?.length">
                <AppBadge v-for="label in opportunity.labels.slice(0, 4)" :key="label" variant="info">{{ label }}</AppBadge>
              </template>
            </div>
            <div v-if="opportunity.knowledge_domains?.length || opportunity.affected_file_count" class="contrib-drawer__feasibility">
              <span v-if="opportunity.knowledge_domains?.length" class="contrib-drawer__feasibility-domains">
                <span class="contrib-drawer__feasibility-label">Area:</span>
                <span v-for="d in opportunity.knowledge_domains" :key="d" class="opp-domain-chip" :title="`This change involves the ${d} area of the codebase`">{{ d.charAt(0).toUpperCase() + d.slice(1) }}</span>
              </span>
              <span v-if="opportunity.affected_file_count" class="contrib-drawer__feasibility-files" title="More files = more complex review process">
                Touches {{ opportunity.affected_file_count }} file{{ opportunity.affected_file_count !== 1 ? 's' : '' }} — {{ opportunity.affected_file_count === 1 ? 'focused change' : 'changes in more files = more complex review' }}
              </span>
            </div>

            <hr class="contrib-drawer__sep" />

            <h4 class="contrib-drawer__section-title">Description</h4>
            <div
              v-if="opportunity.issue_url"
              class="contrib-drawer__md"
              v-html="renderMarkdown(opportunity.description)"
            />
            <p v-else class="contrib-drawer__desc">{{ opportunity.description }}</p>

            <template v-if="opportunity.hints?.length">
              <hr class="contrib-drawer__sep" />
              <h4 class="contrib-drawer__section-title">Where to Start</h4>
              <ul class="contrib-drawer__hints">
                <li v-for="hint in opportunity.hints" :key="hint" class="contrib-drawer__hint" v-html="renderHint(hint)" />
              </ul>
            </template>

            <!-- Issue readiness score -->
            <template v-if="opportunity.readiness_label">
              <hr class="contrib-drawer__sep" />
              <h4 class="contrib-drawer__section-title">Approachability</h4>
              <div class="contrib-drawer__readiness">
                <div :class="['readiness-badge', `readiness-badge--${opportunity.readiness_label.toLowerCase()}`]">
                  {{ opportunity.readiness_label }}
                </div>
                <div class="readiness-bar">
                  <div class="readiness-bar__fill" :style="{ width: `${opportunity.readiness_score}%` }" />
                </div>
                <span class="readiness-score-text">{{ opportunity.readiness_score }}/100</span>
              </div>
            </template>

            <!-- Contributor guidance: suggested files from arch tours -->
            <template v-if="guidanceTour && guidanceSuggestedFiles.length">
              <hr class="contrib-drawer__sep" />
              <h4 class="contrib-drawer__section-title">Where to Look First</h4>
              <div class="contrib-guidance">
                <p class="contrib-guidance__intro">
                  This issue likely touches the <strong>{{ guidanceTour.name }}</strong> area. Start by reading these files:
                </p>
                <div class="contrib-guidance__files">
                  <a
                    v-for="file in guidanceSuggestedFiles"
                    :key="file"
                    :href="githubFileUrl(file) ?? '#'"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="contrib-guidance__file"
                  >{{ file }}</a>
                </div>
              </div>
            </template>

            <template v-if="opportunity.issue_url">
              <hr class="contrib-drawer__sep" />
              <h4 class="contrib-drawer__section-title">GitHub Issue</h4>
              <div class="contrib-drawer__issue-block">
                <a
                  :href="opportunity.issue_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="contrib-drawer__issue-link"
                >
                  View Issue #{{ opportunity.issue_number }} ↗
                </a>
                <p v-if="opportunity.has_open_pr" class="contrib-drawer__pr-note">
                  An open PR already exists for this issue.
                </p>
              </div>
            </template>

            <hr class="contrib-drawer__sep" />
            <p class="contrib-drawer__disclaimer">
              These suggestions are generated from static analysis and heuristics — they may not reflect the full context of the project. Always review the codebase before contributing.
            </p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
