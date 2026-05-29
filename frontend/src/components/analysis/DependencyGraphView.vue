<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import cytoscape from 'cytoscape'
import type { GraphData } from '../../stores/analysis'

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

  const nodes = props.graph.nodes.slice(0, 200).map(n => ({
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
    .slice(0, 500)
    .map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target } }))

  cy = cytoscape({
    container: container.value,
    elements: { nodes, edges },
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'font-size': '10px',
          'text-valign': 'bottom',
          'text-halign': 'center',
          width: 20,
          height: 20,
          'background-color': '#0969da',
          color: '#1f2328',
        },
      },
      {
        selector: 'node[?isGod]',
        style: {
          'background-color': '#cf222e',
          width: 30,
          height: 30,
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
          opacity: 0.6,
        },
      },
    ],
    layout: { name: 'cose', animate: false, randomize: true } as cytoscape.LayoutOptions,
  })
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
