<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { RoadmapMilestone } from '../../stores/analysis'

const props = defineProps<{ milestones: RoadmapMilestone[]; roadmapFile: string }>()

const active = ref<RoadmapMilestone | null>(null)

function open(m: RoadmapMilestone) { active.value = m }
function close() { active.value = null }

function onKey(e: KeyboardEvent) { if (e.key === 'Escape') close() }
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

function statusColor(s: RoadmapMilestone['status']): string {
  return s === 'done' ? 'var(--color-success)' : s === 'in-progress' ? 'var(--color-warning)' : 'var(--color-text-muted)'
}

function statusLabel(s: RoadmapMilestone['status']): string {
  if (s === 'done') return 'Complete'
  if (s === 'in-progress') return 'In progress'
  return 'Planned'
}

function progressPct(m: RoadmapMilestone): number {
  const total = m.done_count + m.todo_count
  if (!total) return m.status === 'done' ? 100 : 0
  return Math.round((m.done_count / total) * 100)
}

const summary = computed(() => {
  let done = 0
  let inProgress = 0
  let planned = 0
  let itemsDone = 0
  let itemsTodo = 0
  for (const m of props.milestones) {
    if (m.status === 'done') done++
    else if (m.status === 'in-progress') inProgress++
    else planned++
    itemsDone += m.done_count
    itemsTodo += m.todo_count
  }
  const itemTotal = itemsDone + itemsTodo
  const overallPct = itemTotal ? Math.round((itemsDone / itemTotal) * 100) : 0
  return { done, inProgress, planned, itemsDone, itemsTodo, overallPct }
})

function previewItems(m: RoadmapMilestone): string[] {
  const open = m.status === 'done' ? m.done_items.slice(-2) : m.todo_items.slice(0, 3)
  return open
}
</script>

<template>
  <div class="roadmap">
    <div class="roadmap__summary">
      <div class="roadmap__summary-main">
        <div class="roadmap__summary-label">Overall progress</div>
        <div class="roadmap__summary-value">{{ summary.overallPct }}%</div>
        <div class="roadmap__progress" role="progressbar" :aria-valuenow="summary.overallPct" aria-valuemin="0" aria-valuemax="100">
          <div class="roadmap__progress-fill" :style="{ width: `${summary.overallPct}%` }" />
        </div>
        <div class="roadmap__summary-meta">
          {{ summary.itemsDone }} done · {{ summary.itemsTodo }} remaining across {{ milestones.length }} milestones
        </div>
      </div>
      <div class="roadmap__stats">
        <div class="roadmap__stat roadmap__stat--done">
          <span class="roadmap__stat-value">{{ summary.done }}</span>
          <span class="roadmap__stat-label">Complete</span>
        </div>
        <div class="roadmap__stat roadmap__stat--progress">
          <span class="roadmap__stat-value">{{ summary.inProgress }}</span>
          <span class="roadmap__stat-label">In progress</span>
        </div>
        <div class="roadmap__stat roadmap__stat--planned">
          <span class="roadmap__stat-value">{{ summary.planned }}</span>
          <span class="roadmap__stat-label">Planned</span>
        </div>
      </div>
    </div>

    <p class="roadmap__hint">Click a milestone for the full checklist · dates come from section headers when present</p>

    <ol class="roadmap__cards">
      <li
        v-for="(m, i) in milestones"
        :key="i"
        :class="['roadmap-card', `roadmap-card--${m.status}`, active?.title === m.title && 'roadmap-card--open']"
        @click="open(m)"
      >
        <div class="roadmap-card__rail">
          <span class="roadmap-card__dot" :style="{ background: statusColor(m.status) }" />
          <span v-if="i < milestones.length - 1" class="roadmap-card__line" />
        </div>
        <div class="roadmap-card__body">
          <div class="roadmap-card__header">
            <span class="roadmap-card__status" :style="{ color: statusColor(m.status) }">{{ statusLabel(m.status) }}</span>
            <span v-if="m.date" class="roadmap-card__date">{{ m.date }}</span>
          </div>
          <h3 class="roadmap-card__title">{{ m.title }}</h3>
          <div class="roadmap-card__progress-row">
            <div class="roadmap-card__progress">
              <div class="roadmap-card__progress-fill" :style="{ width: `${progressPct(m)}%`, background: statusColor(m.status) }" />
            </div>
            <span class="roadmap-card__counts">{{ m.done_count }} / {{ m.done_count + m.todo_count || '—' }}</span>
          </div>
          <ul v-if="previewItems(m).length" class="roadmap-card__preview">
            <li v-for="item in previewItems(m)" :key="item">{{ item }}</li>
          </ul>
          <div v-else class="roadmap-card__empty">No checklist items detected</div>
        </div>
      </li>
    </ol>

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
              <div class="roadmap-drawer__meta">
                <span
                  class="roadmap-drawer__status"
                  :style="{ color: statusColor(active.status) }"
                >{{ statusLabel(active.status) }}</span>
                <span v-if="active.date" class="roadmap-drawer__date">{{ active.date }}</span>
              </div>

              <hr class="h-drawer__divider" />

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
