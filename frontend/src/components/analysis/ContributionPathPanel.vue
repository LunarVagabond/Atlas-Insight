<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ArchTour, ContributionOpportunity } from '../../stores/analysis'

const props = defineProps<{
  tours: ArchTour[]
  opportunities: ContributionOpportunity[]
  repoUrl?: string
  allFiles?: string[]
  embedded?: boolean
}>()

type Area = 'frontend' | 'api' | 'data' | 'tests' | 'config' | 'docs'

const AREA_META: Record<Area, { label: string; icon: string; subsystem_types: string[]; description: string }> = {
  frontend: { label: 'Frontend / UI', icon: '🖥', subsystem_types: ['frontend'], description: 'Work on user-facing code — components, views, styles' },
  api:      { label: 'API / Backend', icon: '🔌', subsystem_types: ['api'], description: 'Routes, controllers, request/response handling' },
  data:     { label: 'Data / Models', icon: '🗄', subsystem_types: ['data'], description: 'Database models, migrations, queries, schemas' },
  tests:    { label: 'Testing', icon: '🧪', subsystem_types: ['tests'], description: 'Add or improve test coverage' },
  config:   { label: 'Infrastructure', icon: '⚙️', subsystem_types: ['config'], description: 'CI/CD, Docker, deployment configuration' },
  docs:     { label: 'Documentation', icon: '📚', subsystem_types: ['docs'], description: 'README, guides, inline docs, changelogs' },
}

const AREA_OPP_CATEGORIES: Record<Area, string[]> = {
  frontend:  ['github-issue', 'feature', 'refactoring'],
  api:       ['github-issue', 'feature', 'security', 'refactoring'],
  data:      ['github-issue', 'feature', 'refactoring'],
  tests:     ['testing'],
  config:    ['ci', 'dependencies'],
  docs:      ['documentation', 'community'],
}

const AREA_PREFIXES: Record<Area, string[]> = {
  frontend: ['src', 'frontend', 'client', 'ui', 'app', 'web', 'pages', 'components'],
  api:      ['api', 'routes', 'routers', 'endpoints', 'controllers', 'views', 'handlers', 'server'],
  data:     ['models', 'db', 'database', 'migrations', 'schemas', 'entities', 'repositories'],
  tests:    ['tests', '__tests__', 'spec', 'specs', 'test', 'e2e', 'integration'],
  config:   ['.github', 'config', 'scripts', 'ci', 'infra', 'deploy', 'k8s', 'docker'],
  docs:     ['docs', 'documentation', 'doc', 'wiki'],
}

const selectedArea = ref<Area | null>(null)

const matchingTour = computed<ArchTour | null>(() => {
  if (!selectedArea.value) return null
  const types = AREA_META[selectedArea.value].subsystem_types
  return props.tours.find(t => types.includes(t.subsystem_type)) ?? null
})

const filteredFallbackFiles = computed<string[]>(() => {
  if (!selectedArea.value || matchingTour.value || !props.allFiles?.length) return []
  const prefixes = AREA_PREFIXES[selectedArea.value]
  return props.allFiles
    .filter(f => prefixes.includes(f.split('/')[0] ?? ''))
    .slice(0, 30)
})

const matchingOpps = computed<ContributionOpportunity[]>(() => {
  if (!selectedArea.value) return []
  const categories = AREA_OPP_CATEGORIES[selectedArea.value]
  return props.opportunities
    .filter(o => categories.includes(o.category))
    .sort((a, b) => {
      const order = { beginner: 0, intermediate: 1, advanced: 2 }
      return order[a.difficulty] - order[b.difficulty]
    })
    .slice(0, 6)
})

function githubFileUrl(file: string): string | null {
  if (!props.repoUrl || !file) return null
  if (file.endsWith('/')) return `${props.repoUrl}/tree/HEAD/${file.slice(0, -1)}`
  return `${props.repoUrl}/blob/HEAD/${file}`
}

function diffVariant(d: ContributionOpportunity['difficulty']) {
  return d === 'beginner' ? 'completed' : d === 'intermediate' ? 'warning' : 'failed'
}

const availableAreas = computed(() =>
  (Object.keys(AREA_META) as Area[]).filter(area => {
    const types = AREA_META[area].subsystem_types
    if (props.tours.some(t => types.includes(t.subsystem_type))) return true
    if (props.allFiles?.length) {
      const prefixes = AREA_PREFIXES[area]
      return props.allFiles.some(f => prefixes.includes(f.split('/')[0] ?? ''))
    }
    return false
  })
)
</script>

<template>
  <div :class="embedded ? 'contrib-path' : 'panel contrib-path'">
    <template v-if="!embedded">
      <h2 class="panel__title">Contribution Path</h2>
      <p class="contrib-path__intro">Pick an area of interest and get a guided reading path + matching contribution opportunities.</p>
    </template>

    <div class="contrib-path__areas">
      <button
        v-for="area in availableAreas"
        :key="area"
        :class="['contrib-path__area-btn', selectedArea === area && 'contrib-path__area-btn--active']"
        @click="selectedArea = selectedArea === area ? null : area"
      >
        <span class="contrib-path__area-icon">{{ AREA_META[area].icon }}</span>
        <span class="contrib-path__area-label">{{ AREA_META[area].label }}</span>
      </button>
    </div>

    <Transition name="fade">
      <div v-if="selectedArea" class="contrib-path__result">
        <p class="contrib-path__area-desc">{{ AREA_META[selectedArea].description }}</p>

        <!-- Reading path from arch tour -->
        <div v-if="matchingTour" class="contrib-path__reading">
          <div class="contrib-path__reading-title">
            <span>{{ AREA_META[selectedArea].icon }}</span>
            Reading Path: {{ matchingTour.name }}
          </div>
          <p class="contrib-path__reading-desc">{{ matchingTour.description }}</p>

          <div v-if="matchingTour.entry_files.length" class="contrib-path__phase">
            <div class="contrib-path__phase-label">1. Start here (entry points)</div>
            <div class="contrib-path__files">
              <a
                v-for="file in matchingTour.entry_files.slice(0, 4)"
                :key="file"
                :href="githubFileUrl(file) ?? '#'"
                target="_blank"
                rel="noopener noreferrer"
                class="contrib-path__file"
              >{{ file }}</a>
            </div>
          </div>

          <div v-if="matchingTour.reading_order.length" class="contrib-path__phase">
            <div class="contrib-path__phase-label">2. Read in order</div>
            <div class="contrib-path__reading-order">
              <div
                v-for="(step, i) in matchingTour.reading_order.slice(0, 6)"
                :key="step.file"
                class="contrib-path__step"
              >
                <span class="contrib-path__step-num">{{ i + 1 }}</span>
                <a
                  :href="githubFileUrl(step.file) ?? '#'"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="contrib-path__step-file"
                >{{ step.file }}</a>
                <span v-if="step.note" class="contrib-path__step-note">{{ step.note }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="filteredFallbackFiles.length" class="contrib-path__reading">
          <div class="contrib-path__reading-title">
            <span>{{ AREA_META[selectedArea].icon }}</span>
            Files in this area
          </div>
          <p class="contrib-path__reading-desc">No curated tour found — showing files matching common {{ AREA_META[selectedArea].label }} directory patterns.</p>
          <div class="contrib-path__files">
            <a
              v-for="file in filteredFallbackFiles"
              :key="file"
              :href="githubFileUrl(file) ?? '#'"
              target="_blank"
              rel="noopener noreferrer"
              class="contrib-path__file"
            >{{ file }}</a>
          </div>
        </div>
        <div v-else class="contrib-path__no-tour">
          No dedicated tour found for this area — explore the <strong>Tours</strong> tab for the full architecture overview.
        </div>

        <!-- Matching opportunities -->
        <div v-if="matchingOpps.length" class="contrib-path__opps">
          <div class="contrib-path__phase-label">3. Contribution opportunities in this area</div>
          <div class="contrib-path__opp-list">
            <div
              v-for="opp in matchingOpps"
              :key="opp.id"
              class="contrib-path__opp"
            >
              <div class="contrib-path__opp-header">
                <span :class="['badge', `badge--${diffVariant(opp.difficulty)}`]">{{ opp.difficulty }}</span>
                <span class="contrib-path__opp-title">{{ opp.title }}</span>
                <a
                  v-if="opp.issue_url"
                  :href="opp.issue_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="contrib-path__opp-issue"
                >#{{ opp.issue_number }} ↗</a>
              </div>
              <p class="contrib-path__opp-desc">{{ opp.description }}</p>
            </div>
          </div>
        </div>
        <div v-else class="contrib-path__no-opps">
          No specific opportunities identified in this area right now.
        </div>
      </div>
    </Transition>
  </div>
</template>
