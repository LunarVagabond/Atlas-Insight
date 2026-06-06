<script setup lang="ts">
import { ref, computed } from 'vue'
import { SUPPORTED_LANGUAGES } from '../data/languages'
import type { SupportMaturity } from '../data/languages'

const query = ref('')

const MATURITY_LABEL: Record<SupportMaturity, string> = {
  experimental: 'Experimental',
  early: 'Beta',
  good: 'Good',
  mature: 'Mature',
}

const TIER_LABEL: Record<string, string> = {
  full: 'Full analysis',
  dependencies: 'Deps only',
}

function matchesQuery(name: string, q: string): boolean {
  return name.toLowerCase().includes(q.toLowerCase())
}

const languages = computed(() => {
  const q = query.value.trim()
  return SUPPORTED_LANGUAGES.filter(l => l.kind === 'language' && (!q || matchesQuery(l.name, q)))
})

const frameworks = computed(() => {
  const q = query.value.trim()
  return SUPPORTED_LANGUAGES.filter(l => l.kind === 'framework' && (!q || matchesQuery(l.name, q)))
})

const tools = computed(() => {
  const q = query.value.trim()
  return SUPPORTED_LANGUAGES.filter(l => l.kind === 'tool' && (!q || matchesQuery(l.name, q)))
})

function maturityClass(m: SupportMaturity | undefined): string {
  return `supported-card__maturity--${m ?? 'early'}`
}
</script>

<template>
  <div class="supported-view">
    <div class="supported-view__hero">
      <h1 class="supported-view__title">What's Supported</h1>
      <p class="supported-view__tagline">Every language, framework, and infrastructure tool Atlas Insight knows how to analyse — with support maturity so you know what to expect.</p>
      <input
        v-model="query"
        type="search"
        class="supported-view__search"
        placeholder="Search languages, frameworks, tools…"
        aria-label="Filter supported technologies"
      />
    </div>

    <div class="supported-view__body">

      <!-- ── Languages ──────────────────────────────────────── -->
      <section class="supported-section">
        <h2 class="supported-section__title">Languages</h2>
        <p class="supported-section__intro">
          "Full analysis" includes the import graph (circular deps, god files, hot files) plus dependency scanning.
          "Deps only" means we scan manifest files but don't trace imports between your source files.
        </p>

        <div v-if="languages.length > 0" class="supported-grid">
          <div v-for="lang in languages" :key="lang.name" class="supported-card">
            <img :src="lang.iconUrl" :alt="lang.name" class="supported-card__icon" loading="lazy" @error="($event.target as HTMLImageElement).style.visibility='hidden'" />
            <div class="supported-card__body">
              <span class="supported-card__name">{{ lang.name }}</span>
              <span class="supported-card__tier" >{{ TIER_LABEL[lang.tier] }}</span>
            </div>
            <span :class="['supported-card__maturity', maturityClass(lang.maturity)]">
              {{ MATURITY_LABEL[lang.maturity ?? 'early'] }}
            </span>
          </div>
        </div>
        <p v-else class="supported-section__empty">No matches for "{{ query }}".</p>
      </section>

      <!-- ── Frameworks ─────────────────────────────────────── -->
      <section class="supported-section">
        <h2 class="supported-section__title">Frameworks &amp; Runtimes</h2>
        <p class="supported-section__intro">
          Detected via dependency manifests. We identify the framework in use and include it in the tech stack — no deep import-graph analysis at the framework level.
        </p>

        <div v-if="frameworks.length > 0" class="supported-grid">
          <div v-for="fw in frameworks" :key="fw.name" class="supported-card">
            <img :src="fw.iconUrl" :alt="fw.name" class="supported-card__icon" loading="lazy" @error="($event.target as HTMLImageElement).style.visibility='hidden'" />
            <div class="supported-card__body">
              <span class="supported-card__name">{{ fw.name }}</span>
              <span class="supported-card__tier" >{{ TIER_LABEL[fw.tier] }}</span>
            </div>
            <span :class="['supported-card__maturity', maturityClass(fw.maturity)]">
              {{ MATURITY_LABEL[fw.maturity ?? 'early'] }}
            </span>
          </div>
        </div>
        <p v-else class="supported-section__empty">No matches for "{{ query }}".</p>
      </section>

      <!-- ── Infrastructure Tools ───────────────────────────── -->
      <section class="supported-section">
        <h2 class="supported-section__title">Infrastructure &amp; Tooling</h2>
        <p class="supported-section__intro">
          These tools get dedicated analysis sections in the DevOps tab — providers, resource counts, hygiene scores, and security issue detection.
          Sections only appear in results when the tool is actually detected in the repo.
        </p>

        <div v-if="tools.length > 0" class="supported-grid">
          <div v-for="tool in tools" :key="tool.name" class="supported-card">
            <img :src="tool.iconUrl" :alt="tool.name" class="supported-card__icon" loading="lazy" @error="($event.target as HTMLImageElement).style.visibility='hidden'" />
            <div class="supported-card__body">
              <span class="supported-card__name">{{ tool.name }}</span>
              <span class="supported-card__tier" >{{ TIER_LABEL[tool.tier] }}</span>
            </div>
            <span :class="['supported-card__maturity', maturityClass(tool.maturity)]">
              {{ MATURITY_LABEL[tool.maturity ?? 'early'] }}
            </span>
          </div>
        </div>
        <p v-else class="supported-section__empty">No matches for "{{ query }}".</p>
      </section>

      <!-- ── Footer ─────────────────────────────────────────── -->
      <div class="supported-view__footer">
        <p>
          Missing something? Language and tool support is community-driven.
          <a href="https://github.com/LunarVagabond/Atlas-Insight/issues" target="_blank" rel="noopener noreferrer">Open an issue</a>
          or check <a href="/docs/dev/adding-a-language" target="_blank">adding a language</a>
          / <a href="/docs/dev/adding-a-tool" target="_blank">adding a tool</a>.
        </p>
      </div>

    </div>
  </div>
</template>
