<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import cytoscape from 'cytoscape'
// @ts-ignore — no types for fcose
import fcose from 'cytoscape-fcose'
import type { GraphData } from '../../stores/analysis'

cytoscape.use(fcose)

const props = defineProps<{ graph: GraphData }>()
const container = ref<HTMLDivElement>()
let cy: cytoscape.Core | null = null

interface NodeInfo {
  id: string
  label: string
  isGod: boolean
  imports: string[]
  importedBy: string[]
}

const FOLDER_PALETTE = [
  '#4A9EFF', '#3DD68C', '#A78BFA', '#F59E0B', '#FB7185',
  '#34D399', '#60A5FA', '#FBBF24', '#C084FC', '#38BDF8',
  '#4ADE80', '#F472B6',
]

function topFolder(id: string): string {
  const parts = id.replace(/^\.{1,2}\//, '').split('/')
  const first = parts[0]
  if (parts.length === 1 || first === '.' || first === '..') return 'root'
  return first
}

function folderColor(name: string): string {
  if (name === 'root') return '#64748B'
  let hash = 0
  for (const c of name) hash = (hash * 31 + c.charCodeAt(0)) & 0xffffffff
  return FOLDER_PALETTE[Math.abs(hash) % FOLDER_PALETTE.length]
}

const GOD_COLOR    = '#ef4444'
const IMPACT_COLOR = '#f97316'

const selectedNode = ref<NodeInfo | null>(null)
const searchQuery = ref('')
const searchMatches = ref<string[]>([])
const searchIndex = ref(0)
const folderFilter = ref(new Set<string>())
const showAllImpact = ref(false)

const folderList = computed(() => {
  const dirs = new Set<string>()
  for (const n of props.graph.nodes.slice(0, 300)) dirs.add(topFolder(n.id))
  return [...dirs].sort((a, b) => a === 'root' ? 1 : b === 'root' ? -1 : a.localeCompare(b))
})

function zoomToMatch(idx: number) {
  if (!cy || !searchMatches.value.length) return
  const id = searchMatches.value[idx]
  const node = cy.getElementById(id)
  cy.elements().removeClass('search-current')
  node.addClass('search-current')
  cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.2), duration: 350, easing: 'ease-in-out-quad' } as Parameters<typeof cy.animate>[0])
}

function searchNodes(q: string) {
  if (!cy || !q.trim()) {
    cy?.elements().removeClass('faded search-match search-current')
    searchMatches.value = []
    searchIndex.value = 0
    return
  }
  const lower = q.toLowerCase()
  const matches = cy.nodes().filter(n => n.id().toLowerCase().includes(lower))
  searchMatches.value = matches.map(n => n.id())
  searchIndex.value = 0

  if (matches.length === 0) {
    cy.elements().removeClass('faded search-match search-current')
    return
  }

  cy.elements().addClass('faded').removeClass('search-match search-current')
  matches.removeClass('faded').addClass('search-match')
  zoomToMatch(0)
}

function stepMatch(dir: 1 | -1) {
  if (!searchMatches.value.length) return
  searchIndex.value = (searchIndex.value + dir + searchMatches.value.length) % searchMatches.value.length
  zoomToMatch(searchIndex.value)
}

function clearSearch() {
  searchQuery.value = ''
  searchMatches.value = []
  searchIndex.value = 0
  cy?.elements().removeClass('faded search-match search-current')
}

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

const impactRadius = computed((): string[] => {
  if (!selectedNode.value) return []
  const idx = edgeIndex.value
  const visited = new Set<string>()
  const queue = [selectedNode.value.id]
  while (queue.length) {
    const cur = queue.shift()!
    for (const dep of (idx.importedBy[cur] ?? [])) {
      if (!visited.has(dep)) {
        visited.add(dep)
        queue.push(dep)
      }
    }
  }
  return [...visited].sort()
})

function selectNode(id: string, isGod: boolean) {
  const idx = edgeIndex.value
  selectedNode.value = {
    id,
    label: id.split('/').pop() ?? id,
    isGod,
    imports: (idx.imports[id] ?? []).sort(),
    importedBy: (idx.importedBy[id] ?? []).sort(),
  }
}

function focusNode(id: string) {
  const godModuleIds = new Set(props.graph.god_modules.map(g => g.module))
  const isGod = godModuleIds.has(id)

  if (cy) {
    cy.elements().removeClass('search-match search-current')
    const node = cy.getElementById(id)
    if (node.nonempty()) {
      node.removeClass('area-hidden')
      cy.elements().removeClass('faded selected impact')
      const neighborhood = node.closedNeighborhood()
      cy.elements().not(neighborhood).not('.area-hidden').addClass('faded')
      neighborhood.addClass('selected')
      node.removeClass('faded')

      const idx = edgeIndex.value
      const visited = new Set<string>()
      const queue = [id]
      while (queue.length) {
        const cur = queue.shift()!
        for (const dep of (idx.importedBy[cur] ?? [])) {
          if (!visited.has(dep)) {
            visited.add(dep)
            queue.push(dep)
          }
        }
      }
      visited.forEach(impId => {
        cy!.getElementById(impId).removeClass('faded').addClass('impact')
      })

      cy.animate({
        center: { eles: node },
        zoom: Math.max(cy.zoom(), 1.2),
        duration: 350,
        easing: 'ease-in-out-quad',
      } as Parameters<typeof cy.animate>[0])
    } else {
      cy.elements().removeClass('faded selected impact')
    }
  }

  selectNode(id, isGod)
  showAllImpact.value = false
}

function closeDrawer() {
  selectedNode.value = null
  showAllImpact.value = false
  cy?.elements().removeClass('faded selected impact')
}

function _applyFolderFilter() {
  if (!cy) return
  if (folderFilter.value.size === 0) {
    cy.elements().removeClass('area-hidden')
    cy.fit(undefined, 32)
    return
  }
  cy.nodes().forEach(node => {
    if (folderFilter.value.has(node.data('folder') as string)) node.removeClass('area-hidden')
    else node.addClass('area-hidden')
  })
  cy.fit(cy.elements(':visible'), 32)
}

function toggleFolder(folder: string) {
  const next = new Set(folderFilter.value)
  if (next.has(folder)) next.delete(folder)
  else next.add(folder)
  folderFilter.value = next
  _applyFolderFilter()
}

function resetFolderFilter() {
  folderFilter.value = new Set()
  _applyFolderFilter()
}

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const LAYOUT_BASE = {
  name: 'fcose',
  quality: 'default',
  animate: true,
  animationDuration: 600,
  fit: true,
  padding: 32,
  nodeRepulsion: 6500,
  idealEdgeLength: 80,
  edgeElasticity: 0.45,
  nestingFactor: 0.1,
  gravity: 0.25,
  gravityRange: 3.8,
  nodeSeparation: 75,
  uniformNodeDimensions: false,
  numIter: 2500,
  tile: true,
  tilingPaddingVertical: 10,
  tilingPaddingHorizontal: 10,
}

function runLayout(options: Record<string, unknown> = {}) {
  if (!cy) return
  cy.layout({ ...LAYOUT_BASE, ...options } as cytoscape.LayoutOptions).run()
}

function initGraph() {
  if (!container.value || !props.graph.nodes.length) return

  if (cy) {
    cy.destroy()
    cy = null
  }

  selectedNode.value = null
  searchQuery.value = ''
  searchMatches.value = []
  searchIndex.value = 0

  const godModuleIds = new Set(props.graph.god_modules.map(g => g.module))

  const nodes = props.graph.nodes.slice(0, 300).map(n => {
    const folder = topFolder(n.id)
    return {
      data: {
        id: n.id,
        label: n.id.split('/').pop() ?? n.id,
        isGod: godModuleIds.has(n.id),
        inDegree: n.in_degree,
        folder,
        color: folderColor(folder),
      },
    }
  })

  const nodeIds = new Set(nodes.map(n => n.data.id))
  const edges = props.graph.edges
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    .slice(0, 600)
    .map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target } }))

  cy = cytoscape({
    container: container.value,
    elements: { nodes, edges },
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'font-size': '9px',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 3,
          width: 16,
          height: 16,
          'background-color': 'data(color)',
          color: cssVar('--color-text'),
        },
      },
      {
        selector: 'node[?isGod]',
        style: {
          'background-color': GOD_COLOR,
          width: 26,
          height: 26,
        },
      },
      {
        selector: 'node.selected',
        style: {
          'background-color': cssVar('--color-success'),
          width: 22,
          height: 22,
          'border-width': 2,
          'border-color': cssVar('--color-text'),
        },
      },
      {
        selector: 'node.faded',
        style: { opacity: 0.2 },
      },
      {
        selector: '.area-hidden',
        style: { display: 'none' },
      },
      {
        selector: 'edge',
        style: {
          width: 1,
          'line-color': cssVar('--color-border'),
          'target-arrow-color': cssVar('--color-border'),
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          opacity: 0.45,
        },
      },
      {
        selector: 'node.search-match',
        style: {
          'background-color': cssVar('--color-warning'),
          width: 18,
          height: 18,
        },
      },
      {
        selector: 'node.search-current',
        style: {
          'background-color': cssVar('--color-warning'),
          'border-width': 3,
          'border-color': cssVar('--color-text'),
          width: 24,
          height: 24,
        },
      },
      {
        selector: 'node.impact',
        style: {
          'background-color': IMPACT_COLOR,
          width: 18,
          height: 18,
          'border-width': 1,
          'border-color': cssVar('--color-text'),
          opacity: 1,
        },
      },
      {
        selector: 'edge.faded',
        style: { opacity: 0.05 },
      },
      {
        selector: 'edge.selected',
        style: {
          'line-color': cssVar('--color-accent'),
          'target-arrow-color': cssVar('--color-accent'),
          opacity: 0.9,
          width: 2,
        },
      },
    ],
    layout: { ...LAYOUT_BASE } as cytoscape.LayoutOptions,
    userZoomingEnabled: true,
    userPanningEnabled: true,
    minZoom: 0.05,
    maxZoom: 4,
  })

  cy.one('layoutstop', () => cy?.fit(undefined, 32))

  cy.on('tap', 'node', (evt) => {
    const node = evt.target as cytoscape.NodeSingular
    focusNode(node.id())
  })

  cy.on('tap', (evt) => {
    if (evt.target === cy) closeDrawer()
  })

  cy.on('drag', 'node', (evt) => {
    const dragged = evt.target as cytoscape.NodeSingular
    const pos = dragged.position()
    const RADIUS = 90
    cy!.nodes().not(dragged).forEach((other) => {
      const opos = other.position()
      const dx = opos.x - pos.x
      const dy = opos.y - pos.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < RADIUS && dist > 0) {
        const push = ((RADIUS - dist) / RADIUS) * 28
        other.position({ x: opos.x + (dx / dist) * push, y: opos.y + (dy / dist) * push })
      }
    })
  })

  cy.on('dragfree', 'node', (evt) => {
    const node = evt.target as cytoscape.NodeSingular
    const pos = { x: node.position().x, y: node.position().y }
    runLayout({
      randomize: false,
      animate: true,
      animationDuration: 500,
      quality: 'draft',
      numIter: 1000,
      fit: false,
      fixedNodeConstraint: [{ nodeId: node.id(), position: pos }],
    })
  })
}

onMounted(() => {
  initGraph()
  const observer = new MutationObserver(initGraph)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
  onUnmounted(() => observer.disconnect())
})
onUnmounted(() => cy?.destroy())
watch(() => props.graph, initGraph)
</script>

<template>
  <div class="dep-graph">
    <div v-if="!graph.nodes.length" class="empty-state">No import data found</div>
    <template v-else>
      <div class="dep-graph__legend">
        <div class="dep-graph__legend-row">
          <span
            v-for="folder in folderList"
            :key="folder"
            class="dep-graph__legend-item"
            :style="{ '--legend-dot': folderColor(folder) }"
          >{{ folder }}</span>
        </div>
        <div class="dep-graph__legend-row">
          <span class="dep-graph__legend-item" :style="{ '--legend-dot': GOD_COLOR }" title="Imported by many other files — changing it could break a lot">Core file</span>
          <span class="dep-graph__legend-item" :style="{ '--legend-dot': IMPACT_COLOR }" title="Files that would need updating if you change the selected file">Affected by change</span>
          <span class="dep-graph__legend-hint">Click any file to see what it imports and what depends on it</span>
        </div>
      </div>
      <div class="dep-graph__filters">
        <span class="dep-graph__filter-label">Filter by folder:</span>
        <button
          class="dep-graph__filter-btn"
          :class="{ 'dep-graph__filter-btn--active': folderFilter.size === 0 }"
          title="Show all files"
          @click="resetFolderFilter()"
        >all</button>
        <button
          v-for="folder in folderList"
          :key="folder"
          class="dep-graph__filter-btn"
          :class="{ 'dep-graph__filter-btn--active': folderFilter.size === 0 || folderFilter.has(folder) }"
          :style="(folderFilter.size === 0 || folderFilter.has(folder)) ? { background: folderColor(folder), borderColor: folderColor(folder), color: '#fff' } : { '--area-color': folderColor(folder) }"
          :title="`Toggle ${folder}/ visibility`"
          @click="toggleFolder(folder)"
        >
          <span class="dep-graph__filter-dot" :style="{ background: folderColor(folder) }" />
          {{ folder }}
        </button>
      </div>
      <div class="dep-graph__stage">
        <div ref="container" class="dep-graph__canvas" />
        <div class="dep-graph__search">
          <input
            v-model="searchQuery"
            class="dep-graph__search-input"
            placeholder="Search nodes…"
            @input="searchNodes(searchQuery)"
            @keydown.escape="clearSearch"
            @keydown.enter.exact="stepMatch(1)"
            @keydown.shift.enter="stepMatch(-1)"
          />
          <template v-if="searchQuery && searchMatches.length > 0">
            <button class="dep-graph__search-step" @click="stepMatch(-1)" title="Previous (Shift+Enter)" aria-label="Previous match">↑</button>
            <span class="dep-graph__search-count" aria-live="polite">{{ searchIndex + 1 }}/{{ searchMatches.length }}</span>
            <button class="dep-graph__search-step" @click="stepMatch(1)" title="Next (Enter)" aria-label="Next match">↓</button>
          </template>
          <span v-else-if="searchQuery && searchMatches.length === 0" class="dep-graph__search-none" role="status">No match</span>
          <button v-if="searchQuery" class="dep-graph__search-clear" @click="clearSearch" title="Clear" aria-label="Clear search">✕</button>
        </div>
        <Transition name="node-drawer">
          <div v-if="selectedNode" class="dep-graph__drawer">
            <div class="dep-graph__drawer-header">
              <div class="dep-graph__drawer-title">
                <span v-if="selectedNode.isGod" class="dep-graph__drawer-god-badge">God module</span>
                <span class="dep-graph__drawer-label" :title="selectedNode.id">{{ selectedNode.label }}</span>
              </div>
              <button class="dep-graph__drawer-close" @click="closeDrawer" title="Close" aria-label="Close file detail">✕</button>
            </div>
            <p class="dep-graph__drawer-path">{{ selectedNode.id }}</p>

            <div class="dep-graph__drawer-section">
              <h4 class="dep-graph__drawer-section-title">
                This file uses
                <span class="dep-graph__drawer-count">{{ selectedNode.imports.length }}</span>
              </h4>
              <div v-if="selectedNode.imports.length" class="dep-graph__drawer-list">
                <button
                  v-for="m in selectedNode.imports"
                  :key="m"
                  type="button"
                  class="dep-graph__drawer-item dep-graph__drawer-item--out"
                  :title="m"
                  @click="focusNode(m)"
                >
                  <span class="dep-graph__drawer-arrow">→</span>
                  <span class="dep-graph__drawer-item-label">{{ m.split('/').pop() }}</span>
                </button>
              </div>
              <p v-else class="dep-graph__drawer-empty">This file doesn't import anything tracked</p>
            </div>

            <div class="dep-graph__drawer-section">
              <h4 class="dep-graph__drawer-section-title">
                Other files that use this
                <span class="dep-graph__drawer-count">{{ selectedNode.importedBy.length }}</span>
              </h4>
              <div v-if="selectedNode.importedBy.length" class="dep-graph__drawer-list">
                <button
                  v-for="m in selectedNode.importedBy"
                  :key="m"
                  type="button"
                  class="dep-graph__drawer-item dep-graph__drawer-item--in"
                  :title="m"
                  @click="focusNode(m)"
                >
                  <span class="dep-graph__drawer-arrow">←</span>
                  <span class="dep-graph__drawer-item-label">{{ m.split('/').pop() }}</span>
                </button>
              </div>
              <p v-else class="dep-graph__drawer-empty">No other files import this one</p>
            </div>

            <div v-if="impactRadius.length" class="dep-graph__drawer-section dep-graph__drawer-section--impact">
              <h4 class="dep-graph__drawer-section-title">
                Change impact
                <span class="dep-graph__drawer-count dep-graph__drawer-count--impact">{{ impactRadius.length }}</span>
              </h4>
              <p class="dep-graph__drawer-impact-hint">
                If you edit this file, {{ impactRadius.length }} other file{{ impactRadius.length !== 1 ? 's' : '' }} could break or need updating (shown in orange on the graph).
              </p>
              <div class="dep-graph__drawer-list">
                <button
                  v-for="m in (showAllImpact ? impactRadius : impactRadius.slice(0, 5))"
                  :key="m"
                  type="button"
                  class="dep-graph__drawer-item dep-graph__drawer-item--impact"
                  :title="m"
                  @click="focusNode(m)"
                >
                  <span class="dep-graph__drawer-arrow">↗</span>
                  <span class="dep-graph__drawer-item-label">{{ m.split('/').pop() }}</span>
                </button>
              </div>
              <button v-if="impactRadius.length > 5" class="dep-graph__show-more" @click="showAllImpact = !showAllImpact">
                {{ showAllImpact ? 'Show less' : `Show all ${impactRadius.length}` }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </template>
  </div>
</template>
