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
              <span class="contrib-drawer__icon">📜</span>
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
