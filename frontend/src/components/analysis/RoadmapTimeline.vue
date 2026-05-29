<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { RoadmapMilestone } from '../../stores/analysis'

defineProps<{ milestones: RoadmapMilestone[]; roadmapFile: string }>()

const active = ref<RoadmapMilestone | null>(null)

function open(m: RoadmapMilestone) { active.value = m }
function close() { active.value = null }

function onKey(e: KeyboardEvent) { if (e.key === 'Escape') close() }
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

function statusColor(s: RoadmapMilestone['status']): string {
  return s === 'done' ? 'var(--color-success)' : s === 'in-progress' ? 'var(--color-warning)' : 'var(--color-text-muted)'
}

function statusLabel(m: RoadmapMilestone): string {
  if (m.status === 'done') return `✓ ${m.done_count} done`
  if (m.status === 'in-progress') return `${m.done_count} done · ${m.todo_count} left`
  return m.todo_count ? `${m.todo_count} planned` : ''
}
</script>

<template>
  <div class="roadmap">
    <div class="roadmap__header">
      <h3 class="roadmap__title">🗺 Roadmap — <span>{{ roadmapFile }}</span></h3>
      <p class="roadmap__hint">Dates extracted from section headers where available · click a node for details</p>
    </div>

    <div class="roadmap__scroll">
      <div class="roadmap__track">
        <div class="roadmap__line" />
        <div
          v-for="(m, i) in milestones"
          :key="i"
          :class="['roadmap__node', `roadmap__node--${m.status}`]"
          @click="open(m)"
        >
          <div class="roadmap__date">{{ m.date ?? '' }}</div>
          <div class="roadmap__dot" :style="{ background: statusColor(m.status) }" />
          <div class="roadmap__label">{{ m.title }}</div>
          <div class="roadmap__counts">{{ statusLabel(m) }}</div>
        </div>
      </div>
    </div>

    <!-- Drawer -->
    <Teleport to="body">
      <Transition name="drawer">
        <div v-if="active" class="h-drawer-root">
          <div class="h-drawer-backdrop" @click="close" />
          <div class="h-drawer" role="dialog" aria-modal="true">
            <div class="h-drawer__header">
              <div class="h-drawer__header-left">
                <span class="h-drawer__icon">🗺</span>
                <span class="h-drawer__title">{{ active.title }}</span>
              </div>
              <button class="h-drawer__close" @click="close" aria-label="Close">✕</button>
            </div>

            <div class="h-drawer__body">
              <!-- Status + date -->
              <div class="roadmap-drawer__meta">
                <span
                  class="roadmap-drawer__status"
                  :style="{ color: statusColor(active.status) }"
                >{{ active.status === 'done' ? '✓ Complete' : active.status === 'in-progress' ? '◑ In Progress' : '○ Planned' }}</span>
                <span v-if="active.date" class="roadmap-drawer__date">{{ active.date }}</span>
              </div>

              <hr class="h-drawer__divider" />

              <!-- Todo items first -->
              <section v-if="active.todo_items.length" class="h-drawer__section">
                <h3 class="h-drawer__section-title">{{ active.status === 'planned' ? 'Planned' : 'Remaining' }}</h3>
                <ul class="roadmap-drawer__list">
                  <li v-for="item in active.todo_items" :key="item" class="roadmap-drawer__item roadmap-drawer__item--todo">
                    <span class="roadmap-drawer__check">○</span>
                    <span>{{ item }}</span>
                  </li>
                </ul>
              </section>

              <hr v-if="active.todo_items.length && active.done_items.length" class="h-drawer__divider" />

              <!-- Completed below -->
              <section v-if="active.done_items.length" class="h-drawer__section">
                <h3 class="h-drawer__section-title">Completed</h3>
                <ul class="roadmap-drawer__list">
                  <li v-for="item in active.done_items" :key="item" class="roadmap-drawer__item roadmap-drawer__item--done">
                    <span class="roadmap-drawer__check">✓</span>
                    <span>{{ item }}</span>
                  </li>
                </ul>
              </section>

              <div v-if="!active.done_items.length && !active.todo_items.length" class="roadmap-drawer__empty">
                No items detected in this section.
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
