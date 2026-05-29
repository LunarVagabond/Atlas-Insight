<script setup lang="ts">
import { computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { GraphData } from '../../stores/analysis'
import { useTableFilter } from '../../composables/useTableFilter'

const props = defineProps<{ graph: GraphData }>()

const godModuleSource = computed(() => props.graph.god_modules)
const hotspotSource = computed(() => props.graph.hotspots)

const godFilter = useTableFilter(godModuleSource, ['module'], 'in_degree' as keyof (typeof props.graph.god_modules)[0])
const hotFilter = useTableFilter(hotspotSource, ['file'], 'degree' as keyof (typeof props.graph.hotspots)[0])
</script>

<template>
  <div class="panel">
    <h2 class="panel__title">Architecture</h2>
    <div class="panel__grid" style="grid-template-columns: repeat(3, 1fr)">
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ graph.node_count }}</div>
          <div class="stat__label">Modules Analyzed</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ graph.cycle_count }}</div>
          <div class="stat__label">Dependency Cycles</div>
        </div>
      </AppCard>
      <AppCard>
        <div class="stat">
          <div class="stat__value">{{ graph.god_modules.length }}</div>
          <div class="stat__label">God Modules</div>
        </div>
      </AppCard>
    </div>

    <div v-if="graph.god_modules.length" style="margin-top: 1.5rem">
      <h3 class="panel__title">God Modules (high in-degree)</h3>
      <input
        v-model="godFilter.query.value"
        class="table-search"
        placeholder="Search modules…"
      />
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="godFilter.setSort('module')">
              Module {{ godFilter.sortIcon('module') }}
            </th>
            <th class="runs-table__sortable" @click="godFilter.setSort('in_degree')">
              Imported By {{ godFilter.sortIcon('in_degree') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in godFilter.filtered.value" :key="m.module">
            <td>{{ m.module }}</td>
            <td><AppBadge variant="warning">{{ m.in_degree }}</AppBadge></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="graph.cycles.length" style="margin-top: 1.5rem">
      <h3 class="panel__title">Circular Dependencies (sample)</h3>
      <div v-for="(cycle, i) in graph.cycles.slice(0, 5)" :key="i" class="cycle-item">
        <code>{{ cycle.join(' → ') }}</code>
      </div>
    </div>

    <div v-if="graph.hotspots.length" style="margin-top: 1.5rem">
      <h3 class="panel__title">File Hotspots</h3>
      <input
        v-model="hotFilter.query.value"
        class="table-search"
        placeholder="Search files…"
      />
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="hotFilter.setSort('file')">
              File {{ hotFilter.sortIcon('file') }}
            </th>
            <th class="runs-table__sortable" @click="hotFilter.setSort('degree')">
              Connections {{ hotFilter.sortIcon('degree') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in hotFilter.filtered.value" :key="h.file">
            <td>{{ h.file }}</td>
            <td>{{ h.degree }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
