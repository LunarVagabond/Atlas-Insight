<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  groups: { label: string; tabs: string[]; color?: string }[]
  modelValue: string
  badges?: Record<string, number | string>
}>()

const emit = defineEmits<{ 'update:modelValue': [tab: string] }>()

const activeGroup = computed(() =>
  props.groups.find(g => g.tabs.includes(props.modelValue)) ?? props.groups[0]
)

function selectGroup(group: { label: string; tabs: string[]; color?: string }) {
  if (!group.tabs.includes(props.modelValue)) {
    emit('update:modelValue', group.tabs[0])
  }
}
</script>

<template>
  <div class="tab-groups">
    <div class="tab-groups__group-row" role="tablist" aria-label="Analysis groups">
      <button
        v-for="group in groups"
        :key="group.label"
        :class="['tab-groups__group-pill', activeGroup?.label === group.label && 'tab-groups__group-pill--active']"
        :style="group.color ? { '--group-color': group.color } : {}"
        type="button"
        @click="selectGroup(group)"
      >
        {{ group.label }}
      </button>
    </div>
    <div
      class="tab-groups__tab-row"
      role="tablist"
      :style="activeGroup?.color ? { '--group-color': activeGroup.color } : {}"
    >
      <button
        v-for="tab in activeGroup?.tabs ?? []"
        :key="tab"
        :class="['tab-groups__tab', modelValue === tab && 'tab-groups__tab--active']"
        type="button"
        role="tab"
        :aria-selected="modelValue === tab"
        @click="emit('update:modelValue', tab)"
      >
        {{ tab }}
        <span v-if="badges?.[tab]" class="tab-groups__badge">{{ badges[tab] }}</span>
      </button>
    </div>
  </div>
</template>
