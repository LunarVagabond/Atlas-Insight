<script setup lang="ts">
import { ref } from 'vue'
import type { ArchTour } from '../../stores/analysis'

const props = defineProps<{
  tours: ArchTour[]
  repoUrl?: string
}>()

const expandedId = ref<string | null>(null)
const copiedId = ref<string | null>(null)

function toggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
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
  <div class="panel">
    <h2 class="panel__title">Architecture Tours</h2>
    <p class="tours-intro">
      Curated reading paths for each major subsystem — generated from the dependency graph, commit history, and project structure.
    </p>

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
  </div>
</template>
