<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ArchTour } from '../../stores/analysis'
import FileHistoryDrawer from './FileHistoryDrawer.vue'

const props = defineProps<{
  tours: ArchTour[]
  repoUrl?: string
  runId?: string
  embedded?: boolean
}>()

const activeFilePath = ref<string | null>(null)
function openFileHistory(file: string) {
  if (!file.endsWith('/')) activeFilePath.value = file
}

const expandedId = ref<string | null>(null)
const copiedId = ref<string | null>(null)

const TOURS_READ_KEY = computed(() =>
  props.runId ? `github-archaeologist:tours-read:${props.runId}` : null
)

function loadReadTours(): Set<string> {
  if (!TOURS_READ_KEY.value) return new Set()
  try {
    const raw = localStorage.getItem(TOURS_READ_KEY.value)
    return new Set(raw ? JSON.parse(raw) : [])
  } catch {
    return new Set()
  }
}

const readTours = ref<Set<string>>(loadReadTours())

function isRead(id: string) { return readTours.value.has(id) }

function markRead(id: string) {
  if (!TOURS_READ_KEY.value || readTours.value.has(id)) return
  readTours.value = new Set([...readTours.value, id])
  localStorage.setItem(TOURS_READ_KEY.value, JSON.stringify([...readTours.value]))
}

function toggle(id: string) {
  const opening = expandedId.value !== id
  expandedId.value = opening ? id : null
  if (opening) markRead(id)
}

function peekFile(tour: ArchTour): string | null {
  const f = tour.entry_files[0]
  if (!f) return null
  const parts = f.split('/')
  return parts[parts.length - 1] ?? null
}

function copyReadingList(tour: ArchTour) {
  const lines = [`# ${tour.name}`, '']
  if (tour.entry_files.length) {
    lines.push('## Entry Points', ...tour.entry_files.map(f => `- ${f}`), '')
  }
  if (tour.reading_order.length) {
    lines.push('## Reading Order')
    tour.reading_order.forEach((s, i) => {
      lines.push(`${i + 1}. ${s.file}${s.note ? ` — ${s.note}` : ''}`)
    })
  }
  navigator.clipboard.writeText(lines.join('\n')).catch(() => {})
  copiedId.value = tour.id
  setTimeout(() => { copiedId.value = null }, 2000)
}

function githubFileUrl(file: string): string | null {
  if (!props.repoUrl) return null
  // Overview tour steps have a trailing slash (directories)
  if (file.endsWith('/')) return `${props.repoUrl}/tree/HEAD/${file.slice(0, -1)}`
  return `${props.repoUrl}/blob/HEAD/${file}`
}

function copyPath(file: string) {
  navigator.clipboard.writeText(file).catch(() => {})
}

const SUBSYSTEM_ICONS: Record<string, string> = {
  frontend: '🖥',
  api: '🔌',
  data: '🗄',
  tests: '🧪',
  config: '⚙️',
  docs: '📚',
  overview: '🗺',
  other: '📁',
}
</script>

<template>
  <div :class="embedded ? 'tours-panel-embedded' : 'panel'">
    <template v-if="!embedded">
      <h2 class="panel__title">Architecture Tours</h2>
      <p class="tours-intro">
        Curated reading paths for each major subsystem — generated from the dependency graph, commit history, and project structure.
      </p>
    </template>

    <div v-if="tours.length" class="tours-grid">
      <div
        v-for="tour in tours"
        :key="tour.id"
        :class="['tour-card', expandedId === tour.id && 'tour-card--expanded']"
        @click="toggle(tour.id)"
      >
        <div class="tour-card__header">
          <span class="tour-card__icon">{{ SUBSYSTEM_ICONS[tour.subsystem_type] ?? '📁' }}</span>
          <div class="tour-card__meta">
            <span class="tour-card__name">{{ tour.name }}</span>
            <div class="tour-card__meta-row">
              <span class="tour-card__count">{{ tour.file_count }} files</span>
              <span v-if="peekFile(tour) && expandedId !== tour.id" class="tour-card__peek">
                → {{ peekFile(tour) }}
              </span>
            </div>
          </div>
          <span v-if="isRead(tour.id) && expandedId !== tour.id" class="tour-card__read-mark" title="You've read this tour">✓</span>
          <span class="tour-card__chevron">{{ expandedId === tour.id ? '▲' : '▼' }}</span>
        </div>
        <p class="tour-card__desc">{{ tour.description }}</p>

        <Transition name="tour-expand">
          <div v-if="expandedId === tour.id" class="tour-card__body" @click.stop>
            <div class="tour-card__body-actions">
              <button class="tour-copy-btn" @click.stop="copyReadingList(tour)">
                {{ copiedId === tour.id ? '✓ Copied' : '⎘ Copy list' }}
              </button>
            </div>
            <!-- Entry Points -->
            <div v-if="tour.entry_files.length" class="tour-section">
              <h4 class="tour-section__title">Entry Points</h4>
              <ul class="tour-file-list">
                <li v-for="f in tour.entry_files" :key="f" class="tour-file">
                  <a
                    v-if="githubFileUrl(f)"
                    :href="githubFileUrl(f)!"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="tour-file__link"
                    @click.stop
                  >{{ f }}</a>
                  <button v-else class="tour-file__copy" @click.stop="copyPath(f)">{{ f }}</button>
                  <button v-if="runId && !f.endsWith('/')" class="file-history-btn" :title="`View commit history for ${f}`" @click.stop="openFileHistory(f)"><svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg></button>
                </li>
              </ul>
            </div>

            <!-- Most-Changed Files -->
            <div v-if="tour.key_files.length" class="tour-section">
              <h4 class="tour-section__title">Most-Changed Files</h4>
              <ul class="tour-file-list">
                <li v-for="kf in tour.key_files" :key="kf.file" class="tour-file">
                  <a
                    v-if="githubFileUrl(kf.file)"
                    :href="githubFileUrl(kf.file)!"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="tour-file__link"
                    @click.stop
                  >{{ kf.file }}</a>
                  <button v-else class="tour-file__copy" @click.stop="copyPath(kf.file)">{{ kf.file }}</button>
                  <span v-if="kf.commit_count" class="tour-file__commits">{{ kf.commit_count }} commits</span>
                  <button v-if="runId && !kf.file.endsWith('/')" class="file-history-btn" :title="`View commit history for ${kf.file}`" @click.stop="openFileHistory(kf.file)"><svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg></button>
                </li>
              </ul>
            </div>

            <!-- Suggested Reading Order -->
            <div v-if="tour.reading_order.length" class="tour-section">
              <h4 class="tour-section__title">Suggested Reading Order</h4>
              <ol class="tour-steps">
                <li v-for="(step, i) in tour.reading_order" :key="step.file" :class="['tour-step', i === 0 && 'tour-step--start']">
                  <span class="tour-step__num">{{ i + 1 }}</span>
                  <div class="tour-step__body">
                    <a
                      v-if="githubFileUrl(step.file)"
                      :href="githubFileUrl(step.file)!"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="tour-file__link"
                      @click.stop
                    >{{ step.file }}</a>
                    <code v-else class="tour-step__file">{{ step.file }}</code>
                    <span v-if="step.note" class="tour-step__note">{{ step.note }}</span>
                  </div>
                </li>
              </ol>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div v-else class="empty-state">
      No architecture tours available — graph data may be insufficient for this repository.
    </div>

    <FileHistoryDrawer
      :run-id="runId ?? null"
      :path="activeFilePath"
      :repo-url="repoUrl"
      @close="activeFilePath = null"
    />
  </div>
</template>
