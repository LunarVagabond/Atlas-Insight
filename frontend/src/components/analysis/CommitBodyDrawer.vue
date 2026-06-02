<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import type { GraphCommit } from './GitGraphSvg.vue'

defineProps<{
  commit: GraphCommit | null
}>()

const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}
</script>

<template>
  <Teleport to="body">
    <Transition name="cm-drawer">
      <div v-if="commit" class="cm-drawer-root">
        <div class="cm-drawer__backdrop" @click="emit('close')" />
        <div class="cm-drawer__panel" role="dialog" aria-modal="true">
          <div class="cm-drawer__header">
            <div class="cm-drawer__title">
              <a
                v-if="commit.commitUrl"
                :href="commit.commitUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="cm-drawer__sha"
              >{{ commit.sha }}</a>
              <span v-else class="cm-drawer__sha cm-drawer__sha--plain">{{ commit.sha }}</span>
              <span class="cm-drawer__count">{{ formatDate(commit.date) }}</span>
            </div>
            <button class="cm-drawer__close" @click="emit('close')" aria-label="Close">✕</button>
          </div>

          <div class="cm-drawer__body">
            <div class="cm-drawer__commit">
              <p class="cm-drawer__message">{{ commit.message }}</p>
              <p class="cm-drawer__author">{{ commit.author }}</p>
            </div>
            <pre v-if="commit.body" class="cb-drawer__body-pre">{{ commit.body }}</pre>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
