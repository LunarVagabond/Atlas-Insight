<script setup lang="ts">
defineProps<{
  tabs: string[]
  modelValue: string
  badges?: Record<string, number | string>
}>()
const emit = defineEmits<{ 'update:modelValue': [tab: string] }>()
</script>

<template>
  <div class="tabs">
    <button
      v-for="tab in tabs"
      :key="tab"
      :class="['tabs__tab', { 'tabs__tab--active': modelValue === tab }]"
      @click="emit('update:modelValue', tab)"
    >
      {{ tab }}
      <span v-if="badges?.[tab]" class="tabs__badge">{{ badges[tab] }}</span>
    </button>
  </div>
</template>
