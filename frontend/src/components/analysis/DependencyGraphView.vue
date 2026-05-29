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
          'background-color': '#0969da',
          color: '#1f2328',
        },
      },
      {
        selector: 'node[?isGod]',
        style: {
          'background-color': '#cf222e',
          width: 26,
          height: 26,
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1,
          'line-color': '#d0d7de',
          'target-arrow-color': '#d0d7de',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          opacity: 0.45,
        },
      },
    ],
    layout: {
      name: 'fcose',
      quality: 'default',
      animate: true,
      animationDuration: 600,
      fit: true,
      padding: 32,
      // repulsion — push nodes apart
      nodeRepulsion: 6500,
      idealEdgeLength: 80,
      edgeElasticity: 0.45,
      nestingFactor: 0.1,
      gravity: 0.25,
      gravityRange: 3.8,
      // prevent overlap
      nodeSeparation: 75,
      uniformNodeDimensions: false,
      // iterations
      numIter: 2500,
      tile: true,
      tilingPaddingVertical: 10,
      tilingPaddingHorizontal: 10,
    } as cytoscape.LayoutOptions,
    userZoomingEnabled: true,
    userPanningEnabled: true,
    minZoom: 0.05,
    maxZoom: 4,
  })

  cy.one('layoutstop', () => cy?.fit(undefined, 32))
}

onMounted(initGraph)
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
