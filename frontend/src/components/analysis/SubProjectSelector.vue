<script setup lang="ts">
import type { SubProject } from '@/types/run'

defineProps<{
  subProjects: SubProject[]
  modelValue: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [name: string | null]
}>()

const LANG_SHORT: Record<string, string> = {
  TypeScript: 'TS',
  JavaScript: 'JS',
  Python: 'Py',
  Go: 'Go',
  Rust: 'Rs',
  Ruby: 'Rb',
  Java: 'Jv',
  'C#': 'C#',
  PHP: 'PHP',
  Swift: 'Sw',
  Vue: 'Vue',
  Dart: 'Dt',
  Elixir: 'Ex',
  Kotlin: 'Kt',
}

function shortLang(languages: string[]): string {
  if (!languages.length) return ''
  return LANG_SHORT[languages[0]] ?? languages[0].slice(0, 3)
}
</script>

<template>
  <div class="subproject-selector">
    <button
      class="subproject-selector__btn"
      :class="{ 'subproject-selector__btn--active': modelValue === null }"
      @click="emit('update:modelValue', null)"
    >
      All
    </button>
    <button
      v-for="sp in subProjects"
      :key="sp.name"
      class="subproject-selector__btn"
      :class="{ 'subproject-selector__btn--active': modelValue === sp.name }"
      @click="emit('update:modelValue', sp.name)"
    >
      {{ sp.name }}
      <span v-if="sp.languages.length" class="subproject-selector__lang">
        {{ shortLang(sp.languages) }}
      </span>
    </button>
  </div>
</template>
