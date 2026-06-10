<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="shortcuts-modal-overlay" @click.self="emit('close')">
    <div class="shortcuts-modal" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
      <div class="shortcuts-modal__header">
        <span class="shortcuts-modal__title">Keyboard Shortcuts</span>
        <button class="shortcuts-modal__close" @click="emit('close')" aria-label="Close">✕</button>
      </div>

      <div class="shortcuts-modal__section">
        <div class="shortcuts-modal__section-title">Navigation (Results page)</div>
        <div class="shortcuts-modal__row">
          <span class="shortcuts-modal__keys"><kbd>j</kbd></span>
          <span class="shortcuts-modal__desc">Previous tab (←)</span>
        </div>
        <div class="shortcuts-modal__row">
          <span class="shortcuts-modal__keys"><kbd>k</kbd></span>
          <span class="shortcuts-modal__desc">Next tab (→)</span>
        </div>
      </div>

      <div class="shortcuts-modal__section">
        <div class="shortcuts-modal__section-title">Global</div>
        <div class="shortcuts-modal__row">
          <span class="shortcuts-modal__keys"><kbd>?</kbd></span>
          <span class="shortcuts-modal__desc">Open this shortcuts guide</span>
        </div>
        <div class="shortcuts-modal__row">
          <span class="shortcuts-modal__keys"><kbd>Esc</kbd></span>
          <span class="shortcuts-modal__desc">Close drawers / modals</span>
        </div>
      </div>
    </div>
  </div>
</template>
