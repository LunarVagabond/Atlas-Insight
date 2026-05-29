<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import cytoscape from 'cytoscape'
// @ts-ignore — no types for fcose
import fcose from 'cytoscape-fcose'
import type { GraphData } from '../../stores/analysis'

cytoscape.use(fcose)

const props = defineProps<{ graph: GraphData }>()
const container = ref<HTMLDivElement>()
let cy: cytoscape.Core | null = null

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
    ],
    layout: { ...LAYOUT_BASE } as cytoscape.LayoutOptions,
    userZoomingEnabled: true,
    userPanningEnabled: true,
    minZoom: 0.05,
    maxZoom: 4,
  })

  cy.one('layoutstop', () => cy?.fit(undefined, 32))

  // push nearby nodes away while dragging
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

  // re-settle graph from current positions when drag ends
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
  // Re-init when theme attribute changes so canvas colors update
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
      </div>
      <div ref="container" class="dep-graph__canvas" />
    </template>
  </div>
</template>
