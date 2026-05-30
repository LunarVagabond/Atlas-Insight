<script setup lang="ts">
import { ref, computed } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import type { GraphData, StructureData } from '../../stores/analysis'
import { useTableFilter } from '../../composables/useTableFilter'

const props = defineProps<{ graph: GraphData; hotFiles?: { file: string; commit_count: number }[]; structure?: StructureData }>()

const hotFilesSource = computed(() => (props.hotFiles ?? []) as Record<string, unknown>[])
const hotFilesFilter = useTableFilter(hotFilesSource, ['file'], 'commit_count', 'desc')

const godModuleSource = computed(() => props.graph.god_modules)
const hotspotSource = computed(() => props.graph.hotspots)

const godFilter = useTableFilter(godModuleSource, ['module'], 'in_degree' as keyof (typeof props.graph.god_modules)[0])
const hotFilter = useTableFilter(hotspotSource, ['file'], 'degree' as keyof (typeof props.graph.hotspots)[0])

// ── File explorer + drawer ────────────────────────────────────────────────────

const edgeIndex = computed(() => {
  const imports: Record<string, string[]> = {}
  const importedBy: Record<string, string[]> = {}
  for (const e of props.graph.edges) {
    if (!imports[e.source]) imports[e.source] = []
    imports[e.source].push(e.target)
    if (!importedBy[e.target]) importedBy[e.target] = []
    importedBy[e.target].push(e.source)
  }
  return { imports, importedBy }
})

interface FileInfo {
  id: string
  label: string
  imports: string[]
  importedBy: string[]
  isGod: boolean
  isHotspot: boolean
  degree: number
}

const godIds = computed(() => new Set(props.graph.god_modules.map(g => g.module)))
const hotspotDegrees = computed(() => {
  const m: Record<string, number> = {}
  for (const h of props.graph.hotspots) m[h.file] = h.degree
  return m
})

function buildFileInfo(id: string): FileInfo {
  const idx = edgeIndex.value
  return {
    id,
    label: id.split('/').pop() ?? id,
    imports: (idx.imports[id] ?? []).sort(),
    importedBy: (idx.importedBy[id] ?? []).sort(),
    isGod: godIds.value.has(id),
    isHotspot: id in hotspotDegrees.value,
    degree: hotspotDegrees.value[id] ?? 0,
  }
}

const drawerFile = ref<FileInfo | null>(null)

function openDrawer(id: string) {
  drawerFile.value = buildFileInfo(id)
}

function closeDrawer() {
  drawerFile.value = null
}

// File explorer search across ALL graph nodes + all_files (deduped)
const explorerQuery = ref('')
const explorerResults = computed(() => {
  const q = explorerQuery.value.trim().toLowerCase()
  if (!q) return []

  // Build unified search set: graph node IDs + all_files paths (deduped)
  const graphIds = new Set(props.graph.nodes.map(n => n.id))
  const allPaths: string[] = [
    ...props.graph.nodes.map(n => n.id),
    ...(props.structure?.all_files ?? []).filter(f => !graphIds.has(f)),
  ]

  return allPaths
    .filter(id => id.toLowerCase().includes(q))
    .slice(0, 40)
    .map(id => ({ id }))
})
</script>

<template>
  <div class="arch-panel">
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

    <!-- File explorer -->
    <div style="margin-top: 1.5rem">
      <h3 class="panel__title">File Explorer</h3>
      <div class="arch-explorer">
        <input
          v-model="explorerQuery"
          class="table-search"
          placeholder="Search any file or module…"
          @keydown.escape="explorerQuery = ''"
        />
        <div v-if="explorerQuery && explorerResults.length" class="arch-explorer__results">
          <button
            v-for="n in explorerResults"
            :key="n.id"
            class="arch-explorer__item"
            :class="{ 'arch-explorer__item--god': godIds.has(n.id), 'arch-explorer__item--hotspot': n.id in hotspotDegrees }"
            @click="openDrawer(n.id)"
          >
            <span class="arch-explorer__item-label" :title="n.id">{{ n.id.split('/').pop() }}</span>
            <span class="arch-explorer__item-path">{{ n.id }}</span>
            <span v-if="godIds.has(n.id)" class="arch-explorer__badge arch-explorer__badge--god">god</span>
            <span v-else-if="n.id in hotspotDegrees" class="arch-explorer__badge arch-explorer__badge--hot">hotspot</span>
          </button>
        </div>
        <p v-else-if="explorerQuery" class="arch-explorer__empty">No modules match "{{ explorerQuery }}"</p>
      </div>
    </div>

    <div v-if="graph.god_modules.length" style="margin-top: 1.5rem">
      <h3 class="panel__title">God Modules <span style="font-size:0.75rem;font-weight:400;color:var(--color-text-muted)">(high in-degree — click to inspect)</span></h3>
      <input v-model="godFilter.query.value" class="table-search" placeholder="Search modules…" />
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="godFilter.setSort('module')">Module {{ godFilter.sortIcon('module') }}</th>
            <th class="runs-table__sortable" @click="godFilter.setSort('in_degree')">Imported By {{ godFilter.sortIcon('in_degree') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in godFilter.filtered.value"
            :key="m.module"
            class="arch-panel__clickable-row"
            @click="openDrawer(m.module)"
          >
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
      <h3 class="panel__title">File Hotspots <span style="font-size:0.75rem;font-weight:400;color:var(--color-text-muted)">(click to inspect)</span></h3>
      <input v-model="hotFilter.query.value" class="table-search" placeholder="Search files…" />
      <table class="data-table">
        <thead>
          <tr>
            <th class="runs-table__sortable" @click="hotFilter.setSort('file')">File {{ hotFilter.sortIcon('file') }}</th>
            <th class="runs-table__sortable" @click="hotFilter.setSort('degree')">Connections {{ hotFilter.sortIcon('degree') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="h in hotFilter.filtered.value"
            :key="h.file"
            class="arch-panel__clickable-row"
            @click="openDrawer(h.file)"
          >
            <td>{{ h.file }}</td>
            <td>{{ h.degree }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="hotFiles?.length" style="margin-top: 1.5rem">
      <h3 class="panel__title">Hot Files <span style="font-size:0.75rem;font-weight:400;color:var(--color-text-muted)">(click to inspect)</span></h3>
      <input v-model="hotFilesFilter.query.value" class="table-search" placeholder="Search files…" />
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th class="runs-table__sortable" @click="hotFilesFilter.setSort('file')">File {{ hotFilesFilter.sortIcon('file') }}</th>
            <th class="runs-table__sortable" @click="hotFilesFilter.setSort('commit_count')">Times Changed {{ hotFilesFilter.sortIcon('commit_count') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(hf, idx) in (hotFilesFilter.filtered.value as any[])"
            :key="hf.file"
            class="arch-panel__clickable-row"
            @click="openDrawer(hf.file)"
          >
            <td>{{ idx + 1 }}</td>
            <td>{{ hf.file }}</td>
            <td>{{ hf.commit_count.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- File drawer — teleported to body so it can be fixed on the right -->
    <Teleport to="body">
      <Transition name="arch-drawer">
        <div v-if="drawerFile" class="arch-file-drawer" @keydown.escape="closeDrawer">
          <div class="arch-file-drawer__backdrop" @click="closeDrawer" />
          <div class="arch-file-drawer__panel">
            <div class="arch-file-drawer__header">
              <div class="arch-file-drawer__title-group">
                <div class="arch-file-drawer__badges">
                  <span v-if="drawerFile.isGod" class="arch-file-drawer__badge arch-file-drawer__badge--god">God module</span>
                  <span v-if="drawerFile.isHotspot" class="arch-file-drawer__badge arch-file-drawer__badge--hot">Hotspot · {{ drawerFile.degree }} connections</span>
                </div>
                <h3 class="arch-file-drawer__filename" :title="drawerFile.id">{{ drawerFile.label }}</h3>
                <p class="arch-file-drawer__path">{{ drawerFile.id }}</p>
              </div>
              <button class="arch-file-drawer__close" @click="closeDrawer" title="Close (Esc)">✕</button>
            </div>

            <div class="arch-file-drawer__body">
              <div class="arch-file-drawer__section">
                <h4 class="arch-file-drawer__section-title">
                  Imports
                  <span class="arch-file-drawer__count">{{ drawerFile.imports.length }}</span>
                </h4>
                <div v-if="drawerFile.imports.length" class="arch-file-drawer__list">
                  <button
                    v-for="m in drawerFile.imports"
                    :key="m"
                    class="arch-file-drawer__entry arch-file-drawer__entry--out"
                    :title="m"
                    @click="openDrawer(m)"
                  >
                    <span class="arch-file-drawer__arrow">→</span>
                    <span class="arch-file-drawer__entry-name">{{ m.split('/').pop() }}</span>
                    <span class="arch-file-drawer__entry-path">{{ m }}</span>
                  </button>
                </div>
                <p v-else class="arch-file-drawer__empty">No outgoing imports</p>
              </div>

              <div class="arch-file-drawer__section">
                <h4 class="arch-file-drawer__section-title">
                  Imported by
                  <span class="arch-file-drawer__count">{{ drawerFile.importedBy.length }}</span>
                </h4>
                <div v-if="drawerFile.importedBy.length" class="arch-file-drawer__list">
                  <button
                    v-for="m in drawerFile.importedBy"
                    :key="m"
                    class="arch-file-drawer__entry arch-file-drawer__entry--in"
                    :title="m"
                    @click="openDrawer(m)"
                  >
                    <span class="arch-file-drawer__arrow">←</span>
                    <span class="arch-file-drawer__entry-name">{{ m.split('/').pop() }}</span>
                    <span class="arch-file-drawer__entry-path">{{ m }}</span>
                  </button>
                </div>
                <p v-else class="arch-file-drawer__empty">Nothing imports this module</p>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
