<script setup lang="ts">
defineProps<{
  lines?: number
  showHeader?: boolean
}>()
</script>

<template>
  <div class="skeleton-card">
    <div v-if="showHeader !== false" class="skeleton-row">
      <div class="skeleton skeleton--circle" style="width:32px;height:32px;flex-shrink:0" />
      <div style="flex:1;display:flex;flex-direction:column;gap:6px">
        <div class="skeleton skeleton--title skeleton--w-1\/2" />
        <div class="skeleton skeleton--text skeleton--w-1\/3" />
      </div>
    </div>
    <div v-for="i in (lines ?? 3)" :key="i" class="skeleton skeleton--text" :style="{ width: `${[100,75,88,60,80][i % 5]}%` }" />
  </div>
</template>
