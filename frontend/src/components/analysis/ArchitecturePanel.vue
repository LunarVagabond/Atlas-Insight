<script setup lang="ts">
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { GraphData } from '../../stores/analysis'

defineProps<{ graph: GraphData }>()
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
      <table class="data-table">
        <thead>
          <tr><th>Module</th><th>Imported By</th></tr>
        </thead>
        <tbody>
          <tr v-for="m in graph.god_modules" :key="m.module">
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
      <table class="data-table">
        <thead>
          <tr><th>File</th><th>Connections</th></tr>
        </thead>
        <tbody>
          <tr v-for="h in graph.hotspots.slice(0, 10)" :key="h.file">
            <td>{{ h.file }}</td>
            <td>{{ h.degree }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
