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

const selectedNode = ref<NodeInfo | null>(null)
const searchQuery = ref('')
const searchMatches = ref<string[]>([])
const searchIndex = ref(0)

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

function closeDrawer() {
  selectedNode.value = null
  cy?.elements().removeClass('faded selected')
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

  const nodes = props.graph.nodes.slice(0, 300).map(n => ({
    data: {
      id: n.id,
      label: n.id.split('/').pop() ?? n.id,
      isGod: godModuleIds.has(n.id),
      inDegree: n.in_degree,
    },
  }))

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
          'background-color': cssVar('--color-accent'),
          color: cssVar('--color-text'),
        },
      },
      {
        selector: 'node[?isGod]',
        style: {
          'background-color': cssVar('--color-error'),
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
    const id = node.id()
    const isGod = node.data('isGod') as boolean

    cy!.elements().removeClass('faded selected')

    const neighborhood = node.closedNeighborhood()
    cy!.elements().not(neighborhood).addClass('faded')
    neighborhood.addClass('selected')
    node.removeClass('faded')

    selectNode(id, isGod)
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
        <span class="dep-graph__legend-item dep-graph__legend-item--normal">Regular module</span>
        <span class="dep-graph__legend-item dep-graph__legend-item--god">God module</span>
        <span class="dep-graph__legend-hint">Click a node to inspect connections</span>
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
            <button class="dep-graph__search-step" @click="stepMatch(-1)" title="Previous (Shift+Enter)">↑</button>
            <span class="dep-graph__search-count">{{ searchIndex + 1 }}/{{ searchMatches.length }}</span>
            <button class="dep-graph__search-step" @click="stepMatch(1)" title="Next (Enter)">↓</button>
          </template>
          <span v-else-if="searchQuery && searchMatches.length === 0" class="dep-graph__search-none">No match</span>
          <button v-if="searchQuery" class="dep-graph__search-clear" @click="clearSearch" title="Clear">✕</button>
        </div>
        <Transition name="node-drawer">
          <div v-if="selectedNode" class="dep-graph__drawer">
            <div class="dep-graph__drawer-header">
              <div class="dep-graph__drawer-title">
                <span v-if="selectedNode.isGod" class="dep-graph__drawer-god-badge">God module</span>
                <span class="dep-graph__drawer-label" :title="selectedNode.id">{{ selectedNode.label }}</span>
              </div>
              <button class="dep-graph__drawer-close" @click="closeDrawer" title="Close">✕</button>
            </div>
            <p class="dep-graph__drawer-path">{{ selectedNode.id }}</p>

            <div class="dep-graph__drawer-section">
              <h4 class="dep-graph__drawer-section-title">
                Imports
                <span class="dep-graph__drawer-count">{{ selectedNode.imports.length }}</span>
              </h4>
              <div v-if="selectedNode.imports.length" class="dep-graph__drawer-list">
                <div
                  v-for="m in selectedNode.imports"
                  :key="m"
                  class="dep-graph__drawer-item dep-graph__drawer-item--out"
                  :title="m"
                >
                  <span class="dep-graph__drawer-arrow">→</span>
                  <span class="dep-graph__drawer-item-label">{{ m.split('/').pop() }}</span>
                </div>
              </div>
              <p v-else class="dep-graph__drawer-empty">No outgoing imports</p>
            </div>

            <div class="dep-graph__drawer-section">
              <h4 class="dep-graph__drawer-section-title">
                Imported by
                <span class="dep-graph__drawer-count">{{ selectedNode.importedBy.length }}</span>
              </h4>
              <div v-if="selectedNode.importedBy.length" class="dep-graph__drawer-list">
                <div
                  v-for="m in selectedNode.importedBy"
                  :key="m"
                  class="dep-graph__drawer-item dep-graph__drawer-item--in"
                  :title="m"
                >
                  <span class="dep-graph__drawer-arrow">←</span>
                  <span class="dep-graph__drawer-item-label">{{ m.split('/').pop() }}</span>
                </div>
              </div>
              <p v-else class="dep-graph__drawer-empty">Nothing imports this module</p>
            </div>
          </div>
        </Transition>
      </div>
    </template>
  </div>
</template>
