<script setup lang="ts">
type Variant = 'pending' | 'running' | 'completed' | 'failed' | 'warning' | 'info'
defineProps<{ variant: Variant; label?: string }>()
</script>

<template>
  <span :class="`badge badge--${variant}`">
    <slot>{{ label }}</slot>
  </span>
</template>
