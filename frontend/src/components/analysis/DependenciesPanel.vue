<script setup lang="ts">
import { computed, ref } from 'vue'
import AppBadge from '../ui/AppBadge.vue'
import AppCard from '../ui/AppCard.vue'
import SubProjectSelector from './SubProjectSelector.vue'
import type { DepsData, SecurityData, SubProject } from '../../stores/analysis'
import { useTableFilter } from '../../composables/useTableFilter'
import { KNOWN_FRAMEWORKS } from '../../composables/frameworkSignals'

type DevFilter = 'all' | 'prod' | 'dev'

const props = defineProps<{
  deps: DepsData
  security?: SecurityData
  subProjects?: SubProject[]
  selectedSubProject?: string | null
}>()

const emit = defineEmits<{ 'update:selectedSubProject': [name: string | null] }>()

const activeDeps = computed<DepsData>(() => {
  if (!props.selectedSubProject || !props.subProjects?.length) return props.deps
  return props.subProjects.find(sp => sp.name === props.selectedSubProject)?.dependencies ?? props.deps
})

const activeSecurity = computed<SecurityData | undefined>(() => {
  if (!props.selectedSubProject || !props.subProjects?.length) return props.security
  return props.subProjects.find(sp => sp.name === props.selectedSubProject)?.security ?? props.security
})

const devFilter = ref<DevFilter>('all')
const showAllDeps = ref(false)

function isFramework(name: string): boolean {
  return name in KNOWN_FRAMEWORKS
}

const regularDepsAll = computed(() =>
  activeDeps.value.dependencies.filter(d => !isFramework(d.name))
)

const depsSource = computed(() => {
  const base = showAllDeps.value ? activeDeps.value.dependencies : regularDepsAll.value
  const all = base as Record<string, unknown>[]
  if (devFilter.value === 'dev') return all.filter(d => d.dev === true)
  if (devFilter.value === 'prod') return all.filter(d => d.dev !== true)
  return all
})
const dockerSource = computed(() => activeDeps.value.docker_issues as Record<string, unknown>[])

const depsFilter = useTableFilter(depsSource, ['name', 'source'], 'name', 'asc')
const dockerFilter = useTableFilter(dockerSource, ['file', 'issue'], 'file', 'asc')

// Vulnerable package names from at-scan-time OSV results
const vulnerableNames = computed<Set<string>>(() => {
  const vulns = activeSecurity.value?.vulnerabilities ?? []
  return new Set(vulns.map(v => v.name.toLowerCase()))
})

const vulnCount = computed(() => activeSecurity.value?.vulnerabilities?.length ?? 0)

function isVulnerable(name: unknown): boolean {
  return vulnerableNames.value.has(String(name).toLowerCase())
}

function versionDisplay(spec: unknown): string {
  if (!spec) return '—'
  const s = String(spec)
  if (s === 'catalog:' || s.startsWith('catalog:')) return 'pnpm catalog'
  return s
}
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Dependencies</h2>

    <SubProjectSelector
      v-if="subProjects?.length"
      :sub-projects="subProjects"
      :model-value="selectedSubProject ?? null"
      style="margin-bottom: 1rem"
      @update:model-value="emit('update:selectedSubProject', $event)"
    />

    <div class="panel__grid" style="grid-template-columns: repeat(2, 1fr); margin-bottom: 1.5rem">
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ activeDeps.dependency_count }}</div>
          <div class="stat__label">Total Dependencies</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ activeDeps.docker_issues.length }}</div>
          <div class="stat__label">Docker Issues</div>
        </div>
      </AppCard>
    </div>

    <div v-if="vulnCount > 0" class="warning-row" style="margin-bottom: 1rem">
      <AppBadge variant="failed">{{ vulnCount }} CVE{{ vulnCount === 1 ? '' : 's' }} found</AppBadge>
      <span>Vulnerable packages are highlighted below — see the <strong>Security</strong> tab for full details.</span>
    </div>

    <div v-if="activeDeps.missing_lockfile_warnings.length" style="margin-bottom: 1.5rem">
      <div v-for="(w, i) in activeDeps.missing_lockfile_warnings" :key="i" class="warning-row">
        <AppBadge variant="warning">Warning</AppBadge>
        <span>{{ w }}</span>
      </div>
    </div>

    <div v-if="activeDeps.docker_issues.length" style="margin-bottom: 1.5rem">
      <h3 class="panel__title">Docker Issues</h3>
      <input
        v-model="dockerFilter.query.value"
        class="table-search"
        placeholder="Search docker issues…"
      />
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="dockerFilter.setSort('file')">
              File {{ dockerFilter.sortIcon('file') }}
            </th>
            <th class="runs-table__sortable" @click="dockerFilter.setSort('issue')">
              Issue {{ dockerFilter.sortIcon('issue') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(issue, i) in dockerFilter.filtered.value" :key="i">
            <td>{{ issue.file }}</td>
            <td><AppBadge variant="warning">{{ issue.issue }}</AppBadge></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="activeDeps.dependencies.length">
      <h3 class="panel__title">
        {{ showAllDeps ? 'All Dependencies' : 'Project Dependencies' }}
        <button class="deps-show-toggle" @click="showAllDeps = !showAllDeps">
          {{ showAllDeps ? 'Hide tech stack' : 'Show all' }}
        </button>
      </h3>
      <div class="table-filter-bar">
        <input
          v-model="depsFilter.query.value"
          class="table-search"
          placeholder="Search packages…"
          style="flex:1"
        />
        <div class="table-filter-bar__group">
          <button
            class="table-filter-bar__btn"
            :class="{ 'table-filter-bar__btn--active': devFilter === 'all' }"
            @click="devFilter = 'all'"
          >All</button>
          <button
            class="table-filter-bar__btn"
            :class="{ 'table-filter-bar__btn--active': devFilter === 'prod' }"
            @click="devFilter = 'prod'"
          >Prod</button>
          <button
            class="table-filter-bar__btn"
            :class="{ 'table-filter-bar__btn--active': devFilter === 'dev' }"
            @click="devFilter = 'dev'"
          >Dev</button>
        </div>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="depsFilter.setSort('name')">
              Package {{ depsFilter.sortIcon('name') }}
            </th>
            <th>Version</th>
            <th class="runs-table__sortable" @click="depsFilter.setSort('source')">
              Source {{ depsFilter.sortIcon('source') }}
            </th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(dep, i) in depsFilter.filtered.value" :key="i" :class="{ 'data-table__row--vuln': isVulnerable(dep.name) }">
            <td>
              <span>{{ dep.name }}</span>
              <AppBadge v-if="isVulnerable(dep.name)" variant="failed" style="margin-left:0.5rem">CVE</AppBadge>
            </td>
            <td>{{ versionDisplay(dep.version_spec) }}</td>
            <td>{{ dep.source }}</td>
            <td>
              <AppBadge v-if="dep.dev" variant="info">dev</AppBadge>
              <AppBadge v-else variant="completed">prod</AppBadge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!activeDeps.dependencies.length && !activeDeps.docker_issues.length" class="empty-state">
      No dependency files found
    </div>
  </div>
</template>
