<script setup lang="ts">
import { computed } from 'vue'
import { SUPPORTED_LANGUAGES } from '../../data/languages'
import type { AnalysisTier, SupportedKind } from '../../data/languages'

const props = withDefaults(defineProps<{
  mode?: 'list' | 'strip' | 'marquee'
  tier?: AnalysisTier | 'all'
  kind?: SupportedKind | 'all'
  limit?: number
}>(), {
  mode: 'list',
  tier: 'all',
  kind: 'all',
  limit: 0,
})

function applyFilters(items: typeof SUPPORTED_LANGUAGES) {
  return items.filter(l =>
    (props.tier === 'all' || l.tier === props.tier) &&
    (props.kind === 'all' || l.kind === props.kind)
  )
}

const filtered = computed(() => {
  const items = applyFilters(SUPPORTED_LANGUAGES)
  return props.limit > 0 ? items.slice(0, props.limit) : items
})

// marquee uses all items (no limit), duplicated for seamless loop
const marqueeItems = computed(() => applyFilters(SUPPORTED_LANGUAGES))

const overflow = computed(() => {
  if (!props.limit) return 0
  return Math.max(0, applyFilters(SUPPORTED_LANGUAGES).length - props.limit)
})
</script>

<template>
  <!-- Marquee mode: infinite scrolling strip -->
  <div v-if="mode === 'marquee'" class="lang-marquee" aria-hidden="true">
    <div class="lang-marquee__track">
      <div v-for="(lang, i) in marqueeItems" :key="'a' + i" class="lang-marquee__item">
        <img :src="lang.iconUrl" :alt="lang.name" class="lang-marquee__icon" loading="lazy" />
        <span class="lang-marquee__name">{{ lang.name }}</span>
      </div>
      <!-- duplicate for seamless loop -->
      <div v-for="(lang, i) in marqueeItems" :key="'b' + i" class="lang-marquee__item" aria-hidden="true">
        <img :src="lang.iconUrl" :alt="lang.name" class="lang-marquee__icon" loading="lazy" />
        <span class="lang-marquee__name">{{ lang.name }}</span>
      </div>
    </div>
  </div>

  <!-- Strip mode: icon row with tooltips -->
  <div v-else-if="mode === 'strip'" class="lang-strip">
    <img
      v-for="lang in filtered"
      :key="lang.name"
      :src="lang.iconUrl"
      :alt="lang.name"
      :title="lang.name"
      class="lang-strip__icon"
      loading="lazy"
    />
    <span v-if="overflow > 0" class="lang-strip__overflow">+{{ overflow }}</span>
  </div>

  <!-- List mode: icon + name + tier badge -->
  <div v-else class="lang-support-list">
    <div v-for="lang in filtered" :key="lang.name" class="lang-support-list__item">
      <img
        :src="lang.iconUrl"
        :alt="lang.name"
        class="lang-support-list__icon"
        loading="lazy"
      />
      <span class="lang-support-list__name">{{ lang.name }}</span>
      <span :class="['lang-support-list__tier', `lang-support-list__tier--${lang.tier}`]">
        {{ lang.tier === 'full' ? 'Full' : 'Deps' }}
      </span>
    </div>
  </div>
</template>
