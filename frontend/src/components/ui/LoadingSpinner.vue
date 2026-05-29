<script setup lang="ts">
defineProps<{ size?: 'default' | 'lg'; label?: string }>()
</script>

<template>
  <div class="loading-state">
    <div :class="['spinner', size === 'lg' && 'spinner--lg']" />
    <span v-if="label">{{ label }}</span>
  </div>
</template>
