<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import AppBadge from '../components/ui/AppBadge.vue'
import AppButton from '../components/ui/AppButton.vue'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'

const router = useRouter()

interface SpotlightItem {
  week_start: string
  repo_url: string
  repo_owner: string
  repo_name: string
  run_id: string | null
  health_label: string | null
  health_key: string | null
  primary_language: string | null
  stars: number | null
  pick_number: number
}

interface SpotlightCurrent {
  run_id: string
  repo_url: string
  repo_owner: string
  repo_name: string
  week_start: string
  stars: number | null
  health_label: string | null
  health_key: string | null
  primary_language: string | null
  topics: string[]
  github_description: string | null
  pick_number: number
}

const QUIPS: Record<string, string[]> = {
  thriving: [
    "This repo is absolutely poppin' 🔥",
    "Velocity? Astronomical.",
    "Chef's kiss level of active",
    "The commit history is immaculate fr",
    "Ship it, ship it, ship it",
    "Actually cooked — and we mean that in a good way",
    "Core devs are eating good rn",
    "If this repo were a restaurant, there'd be a line around the block",
    "Main branch basically lives rent-free in our heads",
    "High throughput. Low drama. Respect.",
  ],
  active: [
    "Healthy commits, healthy vibes",
    "Doing the lord's work, consistently",
    "Solid. No notes.",
    "PRs merged, bugs squashed, vibes maintained",
    "This project hits the gym regularly",
    "Consistent energy. Respect.",
    "Reliable as a Swiss watch, but open source",
    "The kind of project your parents would be proud of",
    "Showing up every week like a pro",
    "Active and thriving — the dream",
  ],
  stable: [
    "Not dead, just resting",
    "Fewer commits, but make 'em count",
    "The strong and silent type of repo",
    "Like a government building — not exciting, but it works",
    "Mature, seasoned, a little gray around the edges",
    "Not chasing hype. Respectable.",
    "The kind of project that just works and you forget it exists. High praise.",
    "\"Battle-tested\" is one way to put it",
    "Slow and steady wins the race... probably",
    "It's giving: dependable legacy codebase energy",
  ],
  declining: [
    "The commits have left the building",
    "One motivated contributor away from a comeback",
    "Could use some love. Any love. Really.",
    "Calling all contributors — we're not crying, you're crying",
    "Still alive! (Barely, but still)",
    "A PR a day keeps the abandonment away",
    "Vibes: end-of-life but make it fashion",
    "This one needs a hug and maybe a maintainer",
    "Somewhere out there, the original author is going \"I should probably push that fix\"",
    "The issue tracker has seen better days",
  ],
  abandoned: [
    "It would be really cool if someone revived this",
    "The last commit is a timestamp of a simpler time",
    "Maintainer said \"I'll be right back\" in 2019",
    "Frozen in time, like a codebase in amber",
    "Not dead, just in cryogenic stasis",
    "A moment of silence... then maybe fork it?",
    "The GitHub equivalent of a ghost town",
    "Every unmaintained repo is just a fork waiting to happen",
    "Somewhere, a star-giver is still hoping",
    "Last seen: a while ago. Reward if found.",
  ],
}

const FALLBACK_QUIPS = [
  "Worth a look",
  "Chosen by the algorithm, blessed by the community",
  "Your weekly dose of open source",
  "We see you, we appreciate you",
  "Atlas Insight approved",
]

function pickQuip(key: string | null): string {
  const pool = (key && QUIPS[key]) ? QUIPS[key] : FALLBACK_QUIPS
  return pool[Math.floor(Math.random() * pool.length)]
}

const current = ref<SpotlightCurrent | null>(null)
const quip = ref('')

watch(current, (val) => {
  quip.value = pickQuip(val?.health_key ?? null)
})
const history = ref<SpotlightItem[]>([])
const total = ref(0)
const page = ref(1)
const perPage = 10
const loading = ref(false)
const currentLoading = ref(false)

type BadgeVariant = 'pending' | 'running' | 'completed' | 'failed' | 'warning' | 'info'
const HEALTH_COLORS: Record<string, BadgeVariant> = {
  thriving: 'completed',
  active: 'completed',
  stable: 'warning',
  declining: 'failed',
  abandoned: 'failed',
}

const totalPages = computed(() => Math.ceil(total.value / perPage))

function formatWeek(isoDate: string) {
  const d = new Date(isoDate + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function pickOrdinal(n: number) {
  const s = [, 'st', 'nd', 'rd'][n % 100 < 11 || n % 100 > 13 ? n % 10 : 0] ?? 'th'
  return `${n}${s}`
}

async function fetchCurrent() {
  currentLoading.value = true
  try {
    const { data } = await axios.get('/api/v1/repositories/spotlight/current')
    current.value = data
  } catch {
    current.value = null
  } finally {
    currentLoading.value = false
  }
}

async function fetchHistory() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/repositories/spotlight/history', {
      params: { page: page.value, per_page: perPage },
    })
    history.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function goToRun(runId: string | null) {
  if (runId) router.push(`/results/${runId}`)
}

onMounted(() => {
  fetchCurrent()
  fetchHistory()
})
</script>

<template>
  <div>
    <!-- Hero spotlight -->
    <div class="spotlight-hero">
      <div class="spotlight-hero__bg-glow" />

      <LoadingSpinner v-if="currentLoading" label="Loading this week's pick…" />

      <div v-else-if="!current" class="spotlight-hero__empty">
        <div class="spotlight-hero__empty-icon">🔭</div>
        <h2 class="spotlight-hero__empty-title">No pick yet this week</h2>
        <p class="spotlight-hero__empty-sub">Check back Monday — a repo will earn the spotlight.</p>
      </div>

      <template v-else>
        <div class="spotlight-hero__eyebrow">
          <span class="spotlight-hero__week-badge">Week of {{ formatWeek(current.week_start) }}</span>
          <span v-if="current.pick_number > 1" class="spotlight-hero__repeat-badge">
            {{ pickOrdinal(current.pick_number) }} time in the spotlight
          </span>
        </div>

        <div class="spotlight-hero__congrats">
          Congratulations to
          <span class="spotlight-hero__author">{{ current.repo_owner }}</span>
        </div>

        <h1 class="spotlight-hero__title">{{ current.repo_owner }}/{{ current.repo_name }}</h1>

        <div class="spotlight-hero__tagline">Repo of the Week</div>

        <p v-if="current.github_description" class="spotlight-hero__desc">
          {{ current.github_description }}
        </p>

        <div class="spotlight-hero__meta">
          <span v-if="current.primary_language" class="spotlight-hero__lang">
            {{ current.primary_language }}
          </span>
          <span v-if="current.stars !== null" class="spotlight-hero__stars">
            ★ {{ current.stars?.toLocaleString() }}
          </span>
          <AppBadge
            v-if="current.health_label && current.health_key"
            :variant="(HEALTH_COLORS[current.health_key] ?? 'info') as BadgeVariant"
          >
            {{ current.health_label }}
          </AppBadge>
        </div>

        <div v-if="current.topics.length" class="spotlight-hero__topics">
          <span v-for="t in current.topics.slice(0, 6)" :key="t" class="spotlight-hero__topic">
            {{ t }}
          </span>
        </div>

        <div class="spotlight-hero__actions">
          <AppButton variant="primary" @click="goToRun(current.run_id)" style="font-size:1rem;padding:12px 28px">
            Read the full analysis →
          </AppButton>
          <a :href="current.repo_url" target="_blank" rel="noopener noreferrer" class="btn btn--secondary" style="font-size:1rem;padding:12px 28px">
            View on GitHub ↗
          </a>
        </div>

        <p v-if="quip" class="spotlight-hero__quip">{{ quip }}</p>
      </template>
    </div>

    <!-- History table -->
    <div class="container" style="margin-top: 3rem; padding-bottom: 3rem">
      <h2 style="font-size:1.25rem;font-weight:700;margin-bottom:1.25rem">Past Spotlights</h2>

      <LoadingSpinner v-if="loading && !history.length" label="Loading history…" />

      <div v-else-if="!history.length" class="empty-state" style="padding: 2rem 0">
        No past spotlights yet.
      </div>

      <template v-else>
        <table class="data-table">
          <thead>
            <tr>
              <th>Week</th>
              <th>Author</th>
              <th>Repository</th>
              <th>Health</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in history"
              :key="item.week_start"
              class="runs-table__row"
              @click="goToRun(item.run_id)"
            >
              <td style="font-family:var(--font-mono);font-size:0.8125rem;color:var(--color-text-muted);white-space:nowrap">
                {{ formatWeek(item.week_start) }}
              </td>
              <td><span class="runs-table__author">{{ item.repo_owner }}</span></td>
              <td>
                <div class="runs-table__repo">
                  <span class="runs-table__project">{{ item.repo_name }}</span>
                  <span v-if="item.primary_language" class="runs-table__url">{{ item.primary_language }}</span>
                </div>
              </td>
              <td>
                <AppBadge
                  v-if="item.health_label && item.health_key"
                  :variant="(HEALTH_COLORS[item.health_key] ?? 'info') as BadgeVariant"
                >
                  {{ item.health_label }}
                </AppBadge>
              </td>
              <td>
                <AppButton
                  v-if="item.run_id"
                  variant="secondary"
                  @click.stop="goToRun(item.run_id)"
                  style="font-size:0.8125rem;padding:4px 12px"
                >
                  View
                </AppButton>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="totalPages > 1" class="runs-pagination" style="margin-top:1.5rem">
          <AppButton variant="secondary" :disabled="page <= 1" @click="page--; fetchHistory()">← Prev</AppButton>
          <span class="runs-pagination__info">Page {{ page }} of {{ totalPages }}</span>
          <AppButton variant="secondary" :disabled="page >= totalPages" @click="page++; fetchHistory()">Next →</AppButton>
        </div>
      </template>
    </div>
  </div>
</template>
