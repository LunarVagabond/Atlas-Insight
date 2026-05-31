<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import type { MonthlyCommit } from '../../stores/analysis'

const props = defineProps<{
  month: string | null
  commits: MonthlyCommit[]
  repoUrl?: string
}>()

const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

function commitUrl(sha: string): string | null {
  if (!props.repoUrl) return null
  return `${props.repoUrl}/commit/${sha}`
}
</script>

<template>
  <Teleport to="body">
    <Transition name="cm-drawer">
      <div v-if="month" class="cm-drawer-root">
        <div class="cm-drawer__backdrop" @click="emit('close')" />
        <div class="cm-drawer__panel" role="dialog" aria-modal="true">
          <div class="cm-drawer__header">
            <div class="cm-drawer__title">
              <span class="cm-drawer__month-label">{{ month }}</span>
              <span class="cm-drawer__count">{{ commits.length }} commit{{ commits.length !== 1 ? 's' : '' }}</span>
            </div>
            <button class="cm-drawer__close" @click="emit('close')" aria-label="Close">✕</button>
          </div>

          <div class="cm-drawer__body">
            <div v-if="commits.length" class="cm-drawer__list">
              <div v-for="c in commits" :key="c.sha" class="cm-drawer__commit">
                <div class="cm-drawer__commit-top">
                  <a
                    v-if="commitUrl(c.sha)"
                    :href="commitUrl(c.sha)!"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="cm-drawer__sha"
                  >{{ c.sha }}</a>
                  <span v-else class="cm-drawer__sha cm-drawer__sha--plain">{{ c.sha }}</span>
                  <span class="cm-drawer__date">{{ c.date }}</span>
                </div>
                <p class="cm-drawer__message">{{ c.message }}</p>
                <p class="cm-drawer__author">{{ c.author }}</p>
              </div>
            </div>
            <p v-else class="cm-drawer__empty">No commit detail available for this month.</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
