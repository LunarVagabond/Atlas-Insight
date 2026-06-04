<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAnalysisStore } from '../../stores/analysis'
import type { PrImpactData } from '../../types/pr-impact'

const props = defineProps<{
  runId: string
  repoUrl?: string
}>()

const store = useAnalysisStore()

const prInput = ref('')
const expanded = ref<number | null>(null)

const parsedPr = computed(() => {
  const raw = prInput.value.trim()
  const match = raw.match(/(\d+)$/)
  return match ? parseInt(match[1], 10) : null
})

const isValidInput = computed(() => parsedPr.value !== null && parsedPr.value > 0)

async function analyze() {
  const pr = parsedPr.value
  if (!pr) return
  if (store.prImpactCache[pr]) {
    expanded.value = pr
    return
  }
  await store.fetchPrImpact(props.runId, pr)
  if (store.prImpactCache[pr]) {
    expanded.value = pr
  }
}

function handleKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && isValidInput.value) analyze()
}

const impact = computed<PrImpactData | null>(() =>
  expanded.value !== null ? (store.prImpactCache[expanded.value] ?? null) : null
)

const isLoading = computed(() => store.prImpactLoading !== null)
const hasError = computed(() => expanded.value !== null && store.prImpactError === expanded.value)

const COMPLEXITY_ICONS: Record<string, string> = {
  low: '🟢',
  medium: '🟡',
  high: '🔴',
}

function prGithubUrl(prNumber: number): string | null {
  if (!props.repoUrl) return null
  return `${props.repoUrl}/pull/${prNumber}`
}

function contributorInitials(author: string): string {
  const parts = author.split(/[\s._@-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return author.slice(0, 2).toUpperCase()
}
</script>

<template>
  <div class="pr-impact">
    <div class="pr-impact__header">
      <span class="pr-impact__icon">🔍</span>
      <div>
        <div class="pr-impact__title">PR Impact Preview</div>
        <div class="pr-impact__subtitle">Estimate review complexity and likely reviewers for a pull request</div>
      </div>
    </div>

    <div class="pr-impact__input-row">
      <input
        v-model="prInput"
        type="text"
        class="pr-impact__input"
        placeholder="PR number or URL (e.g. 42)"
        @keydown="handleKey"
      />
      <button
        class="btn btn--primary pr-impact__btn"
        :disabled="!isValidInput || isLoading"
        @click="analyze"
      >
        {{ isLoading ? 'Analyzing…' : 'Analyze' }}
      </button>
    </div>

    <div v-if="hasError" class="pr-impact__error">
      Could not load PR. Check the number and try again.
    </div>

    <template v-if="impact">
      <div class="pr-impact__result">
        <div class="pr-impact__result-header">
          <a
            v-if="prGithubUrl(impact.pr_number)"
            :href="prGithubUrl(impact.pr_number)!"
            target="_blank"
            rel="noopener noreferrer"
            class="pr-impact__pr-link"
          >#{{ impact.pr_number }} {{ impact.title }}</a>
          <span v-else class="pr-impact__pr-title">#{{ impact.pr_number }} {{ impact.title }}</span>
          <span class="pr-impact__state-badge" :class="`pr-impact__state-badge--${impact.state}`">
            {{ impact.state }}
          </span>
        </div>

        <div class="pr-impact__stats">
          <span class="pr-impact__stat">{{ impact.files_changed }} files</span>
          <span class="pr-impact__stat pr-impact__stat--add">+{{ impact.additions }}</span>
          <span class="pr-impact__stat pr-impact__stat--del">-{{ impact.deletions }}</span>
        </div>

        <div class="pr-impact__complexity" :class="`pr-impact__complexity--${impact.complexity_label}`">
          <span class="pr-impact__complexity-icon">{{ COMPLEXITY_ICONS[impact.complexity_label] }}</span>
          <span class="pr-impact__complexity-label">{{ impact.complexity_label.charAt(0).toUpperCase() + impact.complexity_label.slice(1) }} complexity</span>
          <span class="pr-impact__complexity-score">{{ impact.complexity_score }}/100</span>
        </div>

        <div v-if="impact.complexity_notes.length" class="pr-impact__notes">
          <span v-for="note in impact.complexity_notes" :key="note" class="pr-impact__note">
            {{ note }}
          </span>
        </div>

        <div v-if="impact.touches_god_module || impact.touches_deps" class="pr-impact__flags">
          <span v-if="impact.touches_god_module" class="pr-impact__flag pr-impact__flag--warn">
            Touches highly-imported module
          </span>
          <span v-if="impact.touches_deps" class="pr-impact__flag pr-impact__flag--info">
            Dependency manifest changed
          </span>
        </div>

        <div v-if="impact.affected_subsystems.length" class="pr-impact__section">
          <div class="pr-impact__section-title">Affected subsystems</div>
          <div class="pr-impact__subsystems">
            <div
              v-for="sub in impact.affected_subsystems"
              :key="sub.id"
              class="pr-impact__subsystem"
            >
              <span class="pr-impact__subsystem-name">{{ sub.name }}</span>
              <span class="pr-impact__subsystem-meta">{{ sub.matched_files }} file{{ sub.matched_files !== 1 ? 's' : '' }}</span>
              <span v-if="sub.has_god_modules" class="pr-impact__god-badge" title="Contains a highly-imported module">⚠</span>
            </div>
          </div>
        </div>

        <div v-if="impact.suggested_reviewers.length" class="pr-impact__section">
          <div class="pr-impact__section-title">
            Suggested reviewers
            <span class="pr-impact__section-note">{{
              impact.suggested_reviewers[0].match_reason === 'file_history'
                ? 'by recent commits to these files'
                : impact.suggested_reviewers[0].match_reason === 'subsystem_match'
                  ? 'by subsystem activity'
                  : 'top contributors'
            }}</span>
          </div>
          <div class="pr-impact__reviewers">
            <div
              v-for="reviewer in impact.suggested_reviewers"
              :key="reviewer.author"
              class="pr-impact__reviewer"
              :title="reviewer.email || reviewer.author"
            >
              <span class="pr-impact__reviewer-avatar">{{ contributorInitials(reviewer.author) }}</span>
              <span class="pr-impact__reviewer-name">{{ reviewer.author }}</span>
              <span class="pr-impact__reviewer-meta">
                <template v-if="reviewer.match_reason === 'file_history'">
                  touched {{ reviewer.pr_files_touched }} of these files
                </template>
                <template v-else>active in affected areas</template>
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
