<script setup lang="ts">
defineProps<{
  tabs: string[]
  modelValue: string
  badges?: Record<string, number | string>
}>()
const emit = defineEmits<{ 'update:modelValue': [tab: string] }>()
</script>

<template>
  <div class="tabs" role="tablist">
    <button
      v-for="tab in tabs"
      :key="tab"
      role="tab"
      :aria-selected="modelValue === tab"
      :aria-current="modelValue === tab ? 'true' : undefined"
      :class="['tabs__tab', { 'tabs__tab--active': modelValue === tab }]"
      @click="emit('update:modelValue', tab)"
    >
      {{ tab }}
      <span v-if="badges?.[tab]" class="tabs__badge" :aria-label="`${badges[tab]} items`">{{ badges[tab] }}</span>
    </button>
  </div>
</template>
