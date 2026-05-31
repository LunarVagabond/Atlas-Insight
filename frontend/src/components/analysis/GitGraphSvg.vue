<script setup lang="ts">
import { computed, ref } from 'vue'

// ── Types ─────────────────────────────────────────────────────────────────────
export interface GraphCommit {
  sha: string
  parents: string[]
  message: string
  body?: string | null
  author: string
  date: string           // ISO date string
  color: string
  relativeDate: string
  commitUrl: string | null
}

export interface MonthSep {
  isMonth: true
  label: string
  month: string
  count: number
}

export type GraphRow = GraphCommit | MonthSep

interface ProcessedRow {
  row: GraphRow
  // only for commits:
  lane?: number
  convergingLanes?: number[]  // lanes arriving from top that merge into myLane
  forkLanes?: number[]        // new lanes forking from myLane downward
  beforeLanes?: number[]      // active lane indices entering this row from top
  afterLanes?: number[]       // active lane indices leaving this row at bottom
}

// ── Props & emits ─────────────────────────────────────────────────────────────
const props = defineProps<{
  rows: GraphRow[]
}>()

const emit = defineEmits<{
  clickMonth: [month: string]
}>()

// ── Layout constants ──────────────────────────────────────────────────────────
const ROW_H  = 40   // pixels per commit row
const SEP_H  = 30   // pixels for month separator row
const LANE_W = 16   // pixels between lane centres
const NODE_R = 4    // node circle radius
const GRAPH_PAD = 10 // left padding inside SVG
const DATE_COL_W = 112 // width of date/timeline column on left

// ── Author → lane color ───────────────────────────────────────────────────────
const PALETTE = [
  '#0969da','#7c3aed','#059669','#d97706',
  '#dc2626','#0891b2','#db2777','#65a30d',
  '#ea580c','#4338ca','#0f766e','#b45309',
]

// Each lane index gets a fixed color (lane 0 = first color, etc.)
function laneColor(lane: number): string {
  return PALETTE[lane % PALETTE.length]
}

// ── Lane-assignment algorithm ─────────────────────────────────────────────────
// If no parent data exists at all, fall back to linear single-branch display.
const hasParentData = computed(() =>
  props.rows.some(r => !(r as MonthSep).isMonth && (r as GraphCommit).parents.length > 0)
)

// laneExpects[i] = SHA the lane i is currently pointing at (or null = free)
const processed = computed<ProcessedRow[]>(() => {
  const laneExpects: (string | null)[] = []

  function activeLanes(): number[] {
    return laneExpects.map((s, i) => s !== null ? i : -1).filter(i => i >= 0)
  }

  function freeLane(exclude = -1): number {
    for (let i = 0; i < laneExpects.length; i++) {
      if (i !== exclude && laneExpects[i] === null) return i
    }
    return laneExpects.length
  }

  function ensureLane(i: number) {
    while (laneExpects.length <= i) laneExpects.push(null)
  }

  const result: ProcessedRow[] = []
  let prevAfterLanes: number[] = []

  // Collect commit SHAs in order so we can build synthetic linear parents
  const commitShas = props.rows
    .filter(r => !(r as MonthSep).isMonth)
    .map(r => (r as GraphCommit).sha)

  let commitIdx = 0

  for (const row of props.rows) {
    if ((row as MonthSep).isMonth) {
      result.push({ row, beforeLanes: [...prevAfterLanes], afterLanes: [...prevAfterLanes] })
      continue
    }

    const commit = row as GraphCommit
    const beforeLanes = activeLanes()

    // If no real parent data: synthesize linear parent = next (older) commit
    const effectiveParents = hasParentData.value
      ? commit.parents
      : (commitIdx + 1 < commitShas.length ? [commitShas[commitIdx + 1]] : [])
    commitIdx++

    // Which lanes expect this commit?
    const matching = laneExpects
      .map((s, i) => s === commit.sha ? i : -1)
      .filter(i => i >= 0)

    let myLane: number
    let convergingLanes: number[]

    if (matching.length > 0) {
      myLane = matching[0]
      convergingLanes = matching.slice(1)
      for (const cl of convergingLanes) laneExpects[cl] = null
    } else {
      // Branch head not yet seen — open a new (or free) lane
      myLane = freeLane()
      ensureLane(myLane)
      convergingLanes = []
    }

    // Point this lane at primary parent
    laneExpects[myLane] = effectiveParents[0] ?? null

    // Secondary parents → fork out to new lanes
    const forkLanes: number[] = []
    for (const pSha of effectiveParents.slice(1)) {
      const existing = laneExpects.findIndex(s => s === pSha)
      let fl: number
      if (existing >= 0 && existing !== myLane) {
        fl = existing
      } else {
        fl = freeLane(myLane)
        ensureLane(fl)
        laneExpects[fl] = pSha
      }
      if (!forkLanes.includes(fl)) forkLanes.push(fl)
    }

    // Compact trailing nulls
    while (laneExpects.length && laneExpects[laneExpects.length - 1] === null) laneExpects.pop()

    const afterLanes = activeLanes()
    prevAfterLanes = afterLanes

    result.push({ row: commit, lane: myLane, convergingLanes, forkLanes, beforeLanes, afterLanes })
  }

  return result
})

// ── SVG geometry ──────────────────────────────────────────────────────────────
const BODY_LINE_H = 17
const MAX_BODY_H  = 180

const maxLane = computed(() => {
  let m = 0
  for (const r of processed.value) {
    const lanes = [
      ...(r.beforeLanes ?? []),
      ...(r.afterLanes ?? []),
      ...(r.convergingLanes ?? []),
      ...(r.forkLanes ?? []),
      r.lane ?? 0,
    ]
    if (lanes.length) m = Math.max(m, ...lanes)
  }
  return Math.min(m, 10)
})

const graphWidth = computed(() => GRAPH_PAD * 2 + (maxLane.value + 1) * LANE_W)

// Dynamic row height: expands when body is open
function rowH(r: ProcessedRow): number {
  if ((r.row as MonthSep).isMonth) return SEP_H
  const commit = r.row as GraphCommit
  if (commit.body && expandedShas.value.has(commit.sha)) {
    const lines = commit.body.split('\n').filter(l => l.trim()).length
    return ROW_H + Math.min(lines * BODY_LINE_H + 12, MAX_BODY_H)
  }
  return ROW_H
}

// cumulative Y — reactive to expandedShas changes
const rowY = computed<number[]>(() => {
  void expandedShas.value  // explicit dep
  const ys: number[] = []
  let y = 0
  for (const r of processed.value) {
    ys.push(y)
    y += rowH(r)
  }
  return ys
})

const totalH = computed(() => {
  void expandedShas.value
  const last = processed.value.length - 1
  if (last < 0) return 0
  return rowY.value[last] + rowH(processed.value[last])
})

function lx(lane: number): number {
  return GRAPH_PAD + lane * LANE_W
}

// Bezier path between two (x,y) points — straight if same x, S-curve if different
function path(x1: number, y1: number, x2: number, y2: number): string {
  if (x1 === x2) return `M${x1} ${y1}L${x2} ${y2}`
  const cy = (y1 + y2) / 2
  return `M${x1} ${y1}C${x1} ${cy} ${x2} ${cy} ${x2} ${y2}`
}

// ── Hover / selection ─────────────────────────────────────────────────────────
const hoveredSha = ref<string | null>(null)
const expandedShas = ref<Set<string>>(new Set())

function toggleBody(sha: string) {
  const next = new Set(expandedShas.value)
  if (next.has(sha)) next.delete(sha)
  else next.add(sha)
  expandedShas.value = next
}

function isCommitRow(r: ProcessedRow): r is ProcessedRow & Required<Pick<ProcessedRow,'lane'>> {
  return !(r.row as MonthSep).isMonth
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function authorInitials(name: string): string {
  const clean = name.replace(/\[bot\]/,'').trim()
  const parts = clean.split(/[\s._-]+/).filter(Boolean)
  return parts.length >= 2 ? (parts[0][0]+parts[1][0]).toUpperCase() : clean.slice(0,2).toUpperCase()
}

function isMerge(r: ProcessedRow): boolean {
  return isCommitRow(r) && (r.row as GraphCommit).parents.length > 1
}

function formatDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="gg-container">
    <!-- Date timeline column (left) — month labels live here, not in the graph -->
    <div class="gg-dates" :style="{ height: totalH + 'px', width: DATE_COL_W + 'px' }">
      <template v-for="(r, ridx) in processed" :key="ridx">
        <!-- Month label in timeline — single centered row -->
        <div
          v-if="(r.row as any).isMonth"
          class="gg-date gg-date--month"
          :style="{ height: SEP_H + 'px' }"
          :title="`View ${(r.row as MonthSep).count} commits for ${(r.row as MonthSep).label}`"
          @click="emit('clickMonth', (r.row as MonthSep).month)"
        >
          <span class="gg-date__month-inline">{{ (r.row as MonthSep).label }} <em>({{ (r.row as MonthSep).count }})</em></span>
        </div>
        <!-- Commit date -->
        <div
          v-else
          class="gg-date"
          :class="hoveredSha === (r.row as GraphCommit).sha && 'gg-date--hovered'"
          :style="{ height: rowH(r) + 'px' }"
          @mouseenter="hoveredSha = (r.row as GraphCommit).sha"
          @mouseleave="hoveredSha = null"
        >
          <span class="gg-date__text">{{ formatDate((r.row as GraphCommit).date) }}</span>
          <span class="gg-date__rel">{{ (r.row as GraphCommit).relativeDate }}</span>
        </div>
      </template>
    </div>

    <!-- SVG gutter: branch lines -->
    <svg
      :width="graphWidth"
      :height="totalH"
      class="gg-svg"
      :style="{ width: graphWidth + 'px', height: totalH + 'px', flexShrink: 0 }"
    >
      <template v-for="(r, ridx) in processed" :key="ridx">
        <g :transform="`translate(0, ${rowY[ridx]})`">

          <!-- ── Month separator ── -->
          <template v-if="(r.row as any).isMonth">
            <line
              v-for="lane in (r.beforeLanes ?? [])"
              :key="lane"
              :x1="lx(lane)" y1="0"
              :x2="lx(lane)" :y2="SEP_H"
              :stroke="laneColor(lane)"
              stroke-width="2"
              stroke-opacity="0.25"
            />
          </template>

          <!-- ── Commit row ── -->
          <template v-else>
            <!-- TOP HALF: lanes arriving (node sits at ROW_H/2 regardless of expanded height) -->
            <template v-for="lane in (r.beforeLanes ?? [])" :key="`top-${lane}`">
              <path
                v-if="r.convergingLanes!.includes(lane)"
                :d="path(lx(lane), 0, lx(r.lane!), ROW_H/2)"
                :stroke="laneColor(lane)"
                fill="none" stroke-width="2"
              />
              <line
                v-else-if="lane === r.lane"
                :x1="lx(lane)" y1="0"
                :x2="lx(lane)" :y2="ROW_H/2"
                :stroke="laneColor(lane)"
                stroke-width="2"
              />
              <!-- Pass-through: full row height (including any body expansion) -->
              <line
                v-else
                :x1="lx(lane)" y1="0"
                :x2="lx(lane)" :y2="rowH(r)"
                :stroke="laneColor(lane)"
                stroke-width="2"
              />
            </template>

            <!-- BOTTOM HALF: lanes leaving (from node down to rowH) -->
            <template v-for="lane in (r.afterLanes ?? [])" :key="`bot-${lane}`">
              <path
                v-if="r.forkLanes!.includes(lane) && lane !== r.lane"
                :d="path(lx(r.lane!), ROW_H/2, lx(lane), rowH(r))"
                :stroke="laneColor(lane)"
                fill="none" stroke-width="2"
              />
              <line
                v-else-if="lane === r.lane"
                :x1="lx(lane)" :y1="ROW_H/2"
                :x2="lx(lane)" :y2="rowH(r)"
                :stroke="laneColor(lane)"
                stroke-width="2"
              />
            </template>

            <!-- Node -->
            <circle
              :cx="lx(r.lane!)"
              :cy="ROW_H/2"
              :r="isMerge(r) ? NODE_R + 1 : NODE_R"
              :fill="laneColor(r.lane!)"
              stroke="var(--color-surface)"
              stroke-width="2"
              class="gg-node"
              @mouseenter="hoveredSha = (r.row as GraphCommit).sha"
              @mouseleave="hoveredSha = null"
            />
            <circle
              v-if="isMerge(r)"
              :cx="lx(r.lane!)"
              :cy="ROW_H/2"
              r="2"
              fill="var(--color-surface)"
            />
          </template>
        </g>
      </template>
    </svg>

    <!-- Commit content column -->
    <div class="gg-rows" :style="{ height: totalH + 'px' }">
      <template v-for="(r, ridx) in processed" :key="ridx">
        <!-- Month separator: just a subtle horizontal rule in the graph column -->
        <div
          v-if="(r.row as any).isMonth"
          class="gg-sep-rule"
          :style="{ height: SEP_H + 'px' }"
        />

        <!-- Commit row -->
        <div
          v-else
          :class="['gg-row', hoveredSha === (r.row as GraphCommit).sha && 'gg-row--hovered']"
          :style="{ height: rowH(r) + 'px' }"
          @mouseenter="hoveredSha = (r.row as GraphCommit).sha"
          @mouseleave="hoveredSha = null"
        >
          <!-- Top line: sha + merge badge + message + expand button -->
          <div class="gg-row__top-line" :style="{ height: ROW_H + 'px' }">
            <div class="gg-row__main">
              <a
                v-if="(r.row as GraphCommit).commitUrl"
                :href="(r.row as GraphCommit).commitUrl!"
                target="_blank" rel="noopener noreferrer"
                class="gg-row__sha"
                :style="{ color: laneColor(r.lane ?? 0) }"
                @click.stop
              >{{ (r.row as GraphCommit).sha }}</a>
              <code v-else class="gg-row__sha" :style="{ color: laneColor(r.lane ?? 0) }">
                {{ (r.row as GraphCommit).sha }}
              </code>
              <span v-if="isMerge(r)" class="gg-row__merge-tag">merge</span>
              <span class="gg-row__msg">{{ (r.row as GraphCommit).message.slice(0, 72) }}</span>
              <!-- Expand button shown when body exists -->
              <button
                v-if="(r.row as GraphCommit).body"
                :class="['gg-row__expand-btn', expandedShas.has((r.row as GraphCommit).sha) && 'gg-row__expand-btn--open']"
                :title="expandedShas.has((r.row as GraphCommit).sha) ? 'Collapse commit body' : 'Expand commit body'"
                @click.stop="toggleBody((r.row as GraphCommit).sha)"
              >{{ expandedShas.has((r.row as GraphCommit).sha) ? '▲' : '▼' }}</button>
            </div>
            <!-- Author chip -->
            <span
              class="gg-row__author"
              :style="{ background: laneColor(r.lane ?? 0) + '1a', color: laneColor(r.lane ?? 0), borderColor: laneColor(r.lane ?? 0) + '44' }"
              :title="(r.row as GraphCommit).author"
            >{{ authorInitials((r.row as GraphCommit).author) }}</span>
          </div>

          <!-- Body expansion -->
          <div
            v-if="(r.row as GraphCommit).body && expandedShas.has((r.row as GraphCommit).sha)"
            class="gg-row__body"
          >{{ (r.row as GraphCommit).body }}</div>
        </div>
      </template>
    </div>

  </div>
</template>
