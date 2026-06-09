<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import AppCard from '../ui/AppCard.vue'
import type { RunResult } from '../../stores/analysis'

const props = defineProps<{ result: RunResult }>()

const readme = computed(() => props.result.readme)
const structure = computed(() => props.result.structure)

const expandedFile = ref<string | null>(null)

function toggleFile(key: string) {
  expandedFile.value = key
}

function closeModal() {
  expandedFile.value = null
}

function onModalKey(e: KeyboardEvent) {
  if (e.key === 'Escape') closeModal()
}

function fileContent(key: string): string | null {
  if (key === 'readme') return readme.value?.content ?? null
  return structure.value?.community_files_content?.[key as keyof typeof structure.value.community_files_content] ?? null
}

function isMarkdown(key: string): boolean {
  return key === 'readme'
}

function renderMarkdown(md: string): string {
  return marked.parse(md) as string
}

const readmeQuality = computed(() => readme.value?.quality ?? null)
const readmeMissingRecs = computed(
  () => readmeQuality.value?.recommendations.filter(r => r.status === 'missing') ?? [],
)
const readmeImproveRecs = computed(
  () => readmeQuality.value?.recommendations.filter(r => r.status === 'needs_improvement') ?? [],
)

const communityHealth = computed(() => structure.value?.community_health ?? null)
const communityMissingRecs = computed(
  () => communityHealth.value?.recommendations.filter(r => r.status === 'missing') ?? [],
)
const communityImproveRecs = computed(
  () => communityHealth.value?.recommendations.filter(r => r.status === 'needs_improvement') ?? [],
)

const communityFiles = computed(() => {
  const st = structure.value
  return [
    { key: 'readme', label: 'README', present: readme.value?.found ?? false, icon: '📄', score: readmeQuality.value?.score },
    { key: 'license', label: st?.license_type ? `License (${st.license_type})` : 'License', present: !!st?.license_file || !!st?.license_type, icon: '⚖️', score: fileScore('license') },
    { key: 'contributing', label: 'Contributing Guide', present: !!st?.has_contributing, icon: '🤝', score: fileScore('contributing') },
    { key: 'changelog', label: 'Changelog', present: !!st?.has_changelog, icon: '📋', score: fileScore('changelog') },
    { key: 'coc', label: 'Code of Conduct', present: !!st?.has_coc, icon: '🌐', score: fileScore('coc') },
    { key: 'security', label: 'Security Policy', present: !!st?.has_security_policy, icon: '🔒', score: fileScore('security') },
  ]
})

function fileScore(key: string): number | undefined {
  return communityHealth.value?.files.find(f => f.key === key)?.score
}

const scoringModeLabel = computed(() => {
  const mode = props.result.scoring_mode ?? props.result.oss_score?.mode
  if (mode === 'closed_source') return 'Closed source scoring — present files only'
  return 'Open source scoring — missing community files reduce the score'
})
</script>

<template>
  <div class="panel community-files-panel">
    <h2 class="panel__title">Community Files</h2>
    <p class="community-files-panel__mode-note">{{ scoringModeLabel }}</p>

    <section class="community-files-panel__section">
      <h3 class="community-files-panel__heading">Community Health Files</h3>
      <AppCard>
        <div class="health-grid">
          <div
            v-for="item in communityFiles"
            :key="item.key"
            :class="[
              'health-item',
              item.present ? 'health-item--present' : 'health-item--missing',
              item.present && fileContent(item.key) ? 'health-item--clickable' : '',
            ]"
            @click="item.present && fileContent(item.key) ? toggleFile(item.key) : undefined"
          >
            <span class="health-item__check">{{ item.present ? '✓' : '✗' }}</span>
            <span class="health-item__icon">{{ item.icon }}</span>
            <span class="health-item__label">{{ item.label }}</span>
            <span v-if="item.score != null && item.present" class="health-item__score">{{ Math.round(item.score) }}</span>
            <span v-if="item.present && fileContent(item.key)" class="health-item__expand">↗</span>
          </div>
        </div>
      </AppCard>
    </section>

    <section v-if="communityHealth" class="community-files-panel__section">
      <h3 class="community-files-panel__heading">Community Files Score</h3>
      <div class="readme-quality">
        <div class="readme-quality__score-row">
          <div class="readme-quality__score">{{ communityHealth.score }}<span class="readme-quality__denom">/100</span></div>
          <div v-if="communityHealth.potential_score > communityHealth.score" class="readme-quality__potential">
            Up to {{ communityHealth.potential_score }} if recommendations are applied
          </div>
        </div>
        <div v-if="communityMissingRecs.length" class="readme-quality__group">
          <h4 class="readme-quality__group-title">Missing</h4>
          <ul class="readme-quality__list">
            <li v-for="rec in communityMissingRecs" :key="rec.id" class="readme-quality__item">
              <span class="readme-quality__item-title">{{ rec.title }}</span>
              <span class="readme-quality__gain">+{{ rec.score_gain }}</span>
              <p class="readme-quality__item-desc">{{ rec.description }}</p>
            </li>
          </ul>
        </div>
        <div v-if="communityImproveRecs.length" class="readme-quality__group">
          <h4 class="readme-quality__group-title">Needs improvement</h4>
          <ul class="readme-quality__list">
            <li v-for="rec in communityImproveRecs" :key="rec.id" class="readme-quality__item">
              <span class="readme-quality__item-title">{{ rec.title }}</span>
              <span class="readme-quality__gain">+{{ rec.score_gain }}</span>
              <p class="readme-quality__item-desc">{{ rec.description }}</p>
            </li>
          </ul>
        </div>
      </div>
    </section>
    <section v-else class="community-files-panel__section">
      <p class="empty-state">Re-run analysis to generate community file scores.</p>
    </section>

    <section class="community-files-panel__section">
      <h3 class="community-files-panel__heading">README Quality</h3>
      <div v-if="readmeQuality" class="readme-quality">
        <div class="readme-quality__score-row">
          <div class="readme-quality__score">{{ readmeQuality.score }}<span class="readme-quality__denom">/100</span></div>
          <div v-if="readmeQuality.potential_score > readmeQuality.score" class="readme-quality__potential">
            Up to {{ readmeQuality.potential_score }} if recommendations are applied
          </div>
        </div>
        <div v-if="readmeMissingRecs.length" class="readme-quality__group">
          <h4 class="readme-quality__group-title">Missing</h4>
          <ul class="readme-quality__list">
            <li v-for="rec in readmeMissingRecs" :key="rec.id" class="readme-quality__item">
              <span class="readme-quality__item-title">{{ rec.title }}</span>
              <span class="readme-quality__gain">+{{ rec.score_gain }}</span>
              <p class="readme-quality__item-desc">{{ rec.description }}</p>
            </li>
          </ul>
        </div>
        <div v-if="readmeImproveRecs.length" class="readme-quality__group">
          <h4 class="readme-quality__group-title">Needs improvement</h4>
          <ul class="readme-quality__list">
            <li v-for="rec in readmeImproveRecs" :key="rec.id" class="readme-quality__item">
              <span class="readme-quality__item-title">{{ rec.title }}</span>
              <span class="readme-quality__gain">+{{ rec.score_gain }}</span>
              <p class="readme-quality__item-desc">{{ rec.description }}</p>
            </li>
          </ul>
        </div>
      </div>
      <p v-else class="empty-state">Re-run analysis to generate README quality scores.</p>
    </section>
  </div>

  <Teleport to="body">
    <Transition name="file-modal">
      <div v-if="expandedFile && fileContent(expandedFile)" class="file-modal" @keydown="onModalKey" @click.self="closeModal">
        <div class="file-modal__panel" role="dialog" aria-modal="true">
          <div class="file-modal__header">
            <span class="file-modal__title">
              {{ communityFiles.find(f => f.key === expandedFile)?.icon }}
              {{ communityFiles.find(f => f.key === expandedFile)?.label }}
            </span>
            <button class="file-modal__close" @click="closeModal" aria-label="Close">✕</button>
          </div>
          <div class="file-modal__body">
            <div
              v-if="isMarkdown(expandedFile)"
              class="file-viewer__markdown"
              v-html="renderMarkdown(fileContent(expandedFile)!)"
            />
            <pre v-else class="file-viewer__content">{{ fileContent(expandedFile) }}</pre>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
