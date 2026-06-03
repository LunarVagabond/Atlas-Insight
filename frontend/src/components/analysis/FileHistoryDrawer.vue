<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { FileHistory } from '../../stores/analysis'
import { useAnalysisStore } from '../../stores/analysis'

const props = defineProps<{
  runId: string | null
  path: string | null
  repoUrl?: string
}>()

const emit = defineEmits<{ close: [] }>()

const store = useAnalysisStore()
const history = ref<FileHistory | null>(null)
const loading = ref(false)
const error = ref(false)

watch(() => props.path, async (p) => {
  if (!p || !props.runId) { history.value = null; return }
  loading.value = true
  error.value = false
  history.value = null
  const result = await store.fetchFileHistory(props.runId, p)
  if (result) {
    history.value = result
  } else {
    error.value = true
  }
  loading.value = false
}, { immediate: true })

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function githubFileUrl(file: string): string | null {
  if (!props.repoUrl || !file) return null
  return `${props.repoUrl}/blob/HEAD/${file}`
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
      <div v-if="path" class="contrib-drawer-root">
        <div class="contrib-drawer__backdrop" @click="emit('close')" />
        <div class="contrib-drawer__panel" role="dialog" aria-modal="true">
          <div class="contrib-drawer__header">
            <div class="contrib-drawer__header-left">
              <span class="contrib-drawer__icon">
                <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
              </span>
              <span class="contrib-drawer__category-label">File History</span>
            </div>
            <button class="contrib-drawer__close" @click="emit('close')" aria-label="Close">✕</button>
          </div>

          <div class="contrib-drawer__body">
            <h2 class="contrib-drawer__title file-history__path">{{ path }}</h2>
            <div class="file-history__actions">
              <a v-if="githubFileUrl(path!)" :href="githubFileUrl(path!)!" target="_blank" rel="noopener noreferrer" class="btn btn--secondary btn--sm">
                View on GitHub ↗
              </a>
            </div>

            <div v-if="loading" class="file-history__loading">
              <span class="spinner" />
              <span>Loading commit history…</span>
            </div>

            <div v-else-if="error" class="file-history__error">
              Could not load file history. GitHub API may be unavailable.
            </div>

            <template v-else-if="history">
              <p v-if="!history.commits.length" class="file-history__empty">No commit history found for this file.</p>
              <div v-else class="file-history__timeline">
                <div v-for="commit in history.commits" :key="commit.full_sha" class="fh-commit">
                  <div class="fh-commit__header">
                    <a :href="commit.url" target="_blank" rel="noopener noreferrer" class="fh-commit__sha">{{ commit.sha }}</a>
                    <span class="fh-commit__date">{{ formatDate(commit.date) }}</span>
                    <span class="fh-commit__author">{{ commit.author }}</span>
                  </div>
                  <p class="fh-commit__message">{{ commit.message }}</p>
                  <div v-if="commit.issue_refs.length" class="fh-commit__refs">
                    <span class="fh-commit__refs-label">References:</span>
                    <a
                      v-for="ref in commit.issue_refs"
                      :key="ref"
                      :href="repoUrl ? `${repoUrl}/issues/${ref}` : '#'"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="fh-commit__ref-link"
                    >#{{ ref }}</a>
                  </div>
                </div>
              </div>
              <p class="contrib-drawer__disclaimer">Showing most recent {{ history.commits.length }} commits. View full history on GitHub.</p>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
