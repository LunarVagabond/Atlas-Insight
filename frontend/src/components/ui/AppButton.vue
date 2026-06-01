<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'secondary'
  size?: 'default' | 'sm' | 'lg'
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit'
}>()
</script>

<template>
  <button
    :class="['btn', `btn--${variant ?? 'primary'}`, size === 'lg' && 'btn--lg', size === 'sm' && 'btn--sm']"
    :disabled="disabled || loading"
    :type="type ?? 'button'"
  >
    <span v-if="loading" class="spinner" style="width:16px;height:16px;border-width:2px" />
    <slot />
  </button>
</template>
