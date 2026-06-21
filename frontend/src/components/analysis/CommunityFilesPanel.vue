<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import AppCard from '../ui/AppCard.vue'
import AppTabs from '../ui/AppTabs.vue'
import type { RunResult } from '../../stores/analysis'

const SECTIONS = ['Checklist', 'Scores'] as const

const props = defineProps<{ result: RunResult; section?: string }>()

const emit = defineEmits<{ 'update:section': [section: string] }>()

const activeSection = computed(() =>
  props.section && SECTIONS.includes(props.section as typeof SECTIONS[number])
    ? props.section
    : 'Checklist',
)

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
    { key: 'readme', label: 'README', present: readme.value?.found ?? false, icon: '📄', score: fileEntry('readme')?.score ?? readmeQuality.value?.score },
    { key: 'license', label: st?.license_type ? `License (${st.license_type})` : 'License', present: !!st?.license_file || !!st?.license_type, icon: '⚖️', score: fileEntry('license')?.score },
    { key: 'contributing', label: 'Contributing Guide', present: !!st?.has_contributing, icon: '🤝', score: fileEntry('contributing')?.score },
    { key: 'changelog', label: 'Changelog', present: !!st?.has_changelog, icon: '📋', score: fileEntry('changelog')?.score },
    { key: 'coc', label: 'Code of Conduct', present: !!st?.has_coc, icon: '🌐', score: fileEntry('coc')?.score },
    { key: 'security', label: 'Security Policy', present: !!st?.has_security_policy, icon: '🔒', score: fileEntry('security')?.score },
  ]
})

function fileEntry(key: string) {
  return communityHealth.value?.files.find(f => f.key === key)
}

const scoreBreakdown = computed(() => communityHealth.value?.breakdown ?? [])

const README_CATEGORY_LABELS: Record<string, string> = {
  presence: 'Overview & length',
  getting_started: 'Install & usage',
  examples: 'Code examples',
  visuals: 'Images & badges',
  discoverability: 'Docs links',
  community: 'Community refs',
  engagement: 'Social links',
}

const scoringModeLabel = computed(() => {
  const mode = props.result.scoring_mode ?? props.result.oss_score?.mode
  if (mode === 'closed_source') return 'Closed source scoring — present files only'
  return 'Open source scoring — missing community files reduce the score'
})

interface DocLink {
  label: string
  url: string
  description: string
  badge: string
}

function isDocsLikeUrl(url: string): boolean {
  const low = url.toLowerCase()
  return (
    low.includes('docs.') || low.includes('/docs') || low.includes('/documentation') ||
    low.includes('/wiki') || low.includes('readthedocs') ||
    low.includes('confluence.') || low.includes('notion.so')
  )
}

const docsLinks = computed<DocLink[]>(() => {
  const links: DocLink[] = []
  const seen = new Set<string>()

  function normalise(url: string): string {
    try { return new URL(url).href.replace(/\/$/, '') } catch { return url }
  }

  function push(link: DocLink) {
    const key = normalise(link.url)
    if (!seen.has(key)) { seen.add(key); links.push(link) }
  }

  function hostLabel(url: string): string {
    try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
  }

  function isLocal(url: string): boolean {
    try {
      const h = new URL(url).hostname
      return h === 'localhost' || h === '127.0.0.1' || h === '::1' || h.endsWith('.local')
    } catch { return false }
  }

  const gh = props.result.github_meta
  const readmeData = props.result.readme

  for (const link of readmeData?.docs_links ?? []) {
    if (isLocal(link.url)) continue
    push({
      label: hostLabel(link.url),
      url: link.url,
      description: link.description || 'Documentation link found in README',
      badge: link.label,
    })
  }

  if (gh?.has_wiki && gh?.html_url) {
    push({ label: 'GitHub Wiki', url: `${gh.html_url}/wiki`, description: 'Built-in wiki pages for this repository', badge: 'Wiki' })
  }

  if (gh?.homepage && isDocsLikeUrl(gh.homepage) && !isLocal(gh.homepage)) {
    push({ label: hostLabel(gh.homepage), url: gh.homepage, description: 'Repository homepage links to documentation', badge: 'Homepage' })
  }

  const st = props.result.structure
  if (st?.docs_dir && gh?.html_url) {
    const branch = gh.default_branch ?? 'main'
    push({
      label: `/${st.docs_dir}`,
      url: `${gh.html_url}/tree/${branch}/${st.docs_dir}`,
      description: 'Docs folder in repository root',
      badge: 'Folder',
    })
  }

  return links
})
</script>

<template>
  <div class="panel community-files-panel">
    <h2 class="panel__title">Community Files</h2>
    <p class="community-files-panel__mode-note">{{ scoringModeLabel }}</p>

    <div class="panel__sub-tabs">
      <AppTabs
        :tabs="[...SECTIONS]"
        :model-value="activeSection"
        @update:model-value="emit('update:section', $event)"
      />
    </div>

    <section v-if="activeSection === 'Checklist'" class="community-files-panel__section">
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

    <section v-if="activeSection === 'Checklist' && docsLinks.length" class="community-files-panel__section">
      <h3 class="community-files-panel__heading">Documentation Links</h3>
      <AppCard>
        <ul class="doc-links">
          <li v-for="link in docsLinks" :key="link.url" class="doc-links__item">
            <span class="doc-links__badge">{{ link.badge }}</span>
            <a :href="link.url" target="_blank" rel="noopener noreferrer" class="doc-links__label">{{ link.label }} ↗</a>
            <span class="doc-links__desc">{{ link.description }}</span>
          </li>
        </ul>
      </AppCard>
    </section>

    <template v-else-if="activeSection === 'Scores'">
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
        <div v-if="scoreBreakdown.length" class="community-files-panel__breakdown">
          <h4 class="readme-quality__group-title">Score breakdown</h4>
          <p class="community-files-panel__breakdown-note">
            Each row shows how much a file drags the overall score below a perfect 100.
          </p>
          <table class="community-files-panel__breakdown-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Score</th>
                <th>Weight</th>
                <th>Contributes</th>
                <th>Gap</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scoreBreakdown" :key="row.key">
                <td>{{ row.label }}</td>
                <td>{{ Math.round(row.score) }}</td>
                <td>{{ Math.round(row.weight * 100) }}%</td>
                <td>{{ row.weighted_score }}</td>
                <td class="community-files-panel__gap">−{{ row.gap }}</td>
              </tr>
            </tbody>
          </table>
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
        <div v-if="readmeQuality.categories.length" class="community-files-panel__breakdown">
          <h4 class="readme-quality__group-title">Category breakdown</h4>
          <table class="community-files-panel__breakdown-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Score</th>
                <th>Weight</th>
                <th>Weighted</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="cat in readmeQuality.categories" :key="cat.key">
                <td>{{ README_CATEGORY_LABELS[cat.key] ?? cat.key }}</td>
                <td>{{ Math.round(cat.score) }}</td>
                <td>{{ Math.round(cat.weight * 100) }}%</td>
                <td>{{ cat.weighted_score }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p v-else class="empty-state">Re-run analysis to generate README quality scores.</p>
    </section>
    </template>
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
