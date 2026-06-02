<script setup lang="ts">
import { useToast } from '../../composables/useToast'

const { toasts, dismiss } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast--${toast.variant}`]"
          role="alert"
        >
          <span class="toast__message">{{ toast.message }}</span>
          <button class="toast__close" @click="dismiss(toast.id)" aria-label="Dismiss">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
