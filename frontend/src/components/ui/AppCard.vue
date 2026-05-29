<script setup lang="ts">
defineProps<{ elevated?: boolean }>()
</script>

<template>
  <div :class="['card', { 'card--elevated': elevated }]">
    <slot />
  </div>
</template>
