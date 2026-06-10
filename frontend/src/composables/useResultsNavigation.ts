import { ref, computed, watch, type ComputedRef, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

export const CHAPTER_GROUPS = [
  { label: 'Health', tabs: ['Overview', 'Heuristics', 'Security', 'Licenses', 'Dependencies'], color: '#f59e0b' },
  { label: 'Codebase', tabs: ['Architecture', 'Code Quality', 'Repository', 'Roadmap', 'Ownership'], color: '#6366f1' },
  { label: 'Community', tabs: ['Contributing', 'Tours', 'Community Files', 'Leaderboards', 'DevOps'], color: '#22c55e' },
] as const

export const DOCS_ONLY_TABS: Set<string> = new Set([
  'Overview', 'Repository', 'Roadmap', 'Ownership', 'Security', 'Contributing', 'Community Files',
])

export const TAB_SECTIONS: Record<string, readonly string[] | null> = {
  Overview: null,
  Heuristics: ['Summary', 'Signals'],
  Security: ['Patterns', 'CVEs'],
  Licenses: null,
  Dependencies: ['Packages', 'Containers'],
  Architecture: ['Explorer', 'Graph'],
  'Code Quality': ['Tests', 'Complexity', 'Dead Code', 'Clutter'],
  Repository: ['Profile', 'Activity', 'Branches'],
  Ownership: null,
  Contributing: null,
  Tours: ['Guided', 'Start Here'],
  'Community Files': ['Checklist', 'Scores'],
  Leaderboards: null,
  DevOps: ['CI/CD', 'Containers', 'Changelog', 'Infrastructure'],
}

export const LEGACY_TAB_MAP: Record<string, { tab: string; section?: string }> = {
  Project: { tab: 'Repository', section: 'Profile' },
  History: { tab: 'Repository', section: 'Activity' },
  'Contribution Path': { tab: 'Tours', section: 'Start Here' },
}

export function resolveTabFromQuery(
  rawTab: string | undefined,
  rawSection: string | undefined,
  availableTabs: string[],
): { tab: string; section: string | null } {
  let tab = rawTab || 'Overview'
  let section = rawSection ?? null

  const legacy = LEGACY_TAB_MAP[tab]
  if (legacy) {
    tab = legacy.tab
    section = legacy.section ?? section
  }

  if (!availableTabs.includes(tab)) {
    return { tab: 'Overview', section: null }
  }

  const sections = TAB_SECTIONS[tab]
  if (sections) {
    if (!section || !sections.includes(section)) {
      section = sections[0]
    }
  } else {
    section = null
  }

  return { tab, section }
}

export function sectionsForTab(tab: string): string[] | null {
  const s = TAB_SECTIONS[tab]
  return s ? [...s] : null
}

type NavPosition = { tab: string; section: string | null }

export function buildNavPositions(tabs: string[]): NavPosition[] {
  const positions: NavPosition[] = []
  for (const tab of tabs) {
    const sections = sectionsForTab(tab)
    if (!sections) positions.push({ tab, section: null })
    else for (const section of sections) positions.push({ tab, section })
  }
  return positions
}

function navIndex(positions: NavPosition[], pos: NavPosition): number {
  const idx = positions.findIndex(p => p.tab === pos.tab && p.section === pos.section)
  return idx >= 0 ? idx : 0
}

export function useResultsNavigation(
  route: RouteLocationNormalizedLoaded,
  router: Router,
  tabs: ComputedRef<string[]>,
  scrollRef?: Ref<HTMLElement | null>,
) {
  const initial = resolveTabFromQuery(
    route.query.tab as string | undefined,
    route.query.section as string | undefined,
    tabs.value,
  )
  const activeTab = ref(initial.tab)
  const activeSection = ref<string | null>(initial.section)

  const activeChapterIndex = computed(() => tabs.value.indexOf(activeTab.value))

  const chapterPositionLabel = computed(() => {
    const sections = sectionsForTab(activeTab.value)
    if (sections && activeSection.value) {
      return `${activeTab.value} · ${activeSection.value} — Ch.${activeChapterIndex.value + 1} / ${tabs.value.length}`
    }
    return `Ch.${activeChapterIndex.value + 1} / ${tabs.value.length}`
  })

  const navPositions = computed(() => buildNavPositions(tabs.value))

  const prevNav = computed<NavPosition | null>(() => {
    const positions = navPositions.value
    const cur = navIndex(positions, { tab: activeTab.value, section: activeSection.value })
    if (cur <= 0) return null
    return positions[cur - 1]
  })

  const nextNav = computed<NavPosition | null>(() => {
    const positions = navPositions.value
    const cur = navIndex(positions, { tab: activeTab.value, section: activeSection.value })
    if (cur >= positions.length - 1) return null
    return positions[cur + 1]
  })

  const prevChapterLabel = computed(() => {
    const p = prevNav.value
    if (!p) return null
    const sections = sectionsForTab(p.tab)
    if (sections && p.section && sections.length > 1) return `${p.tab} · ${p.section}`
    return p.tab
  })

  const nextChapterLabel = computed(() => {
    const n = nextNav.value
    if (!n) return null
    const sections = sectionsForTab(n.tab)
    if (sections && n.section && sections.length > 1) return `${n.tab} · ${n.section}`
    return n.tab
  })

  function applyNav(pos: NavPosition) {
    activeTab.value = pos.tab
    activeSection.value = pos.section
    scrollRef?.value?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function goToChapter(tab: string, section?: string | null) {
    const sections = sectionsForTab(tab)
    applyNav({
      tab,
      section: sections ? (section && sections.includes(section) ? section : sections[0]) : null,
    })
  }

  function navigate(delta: 1 | -1) {
    const target = delta === 1 ? nextNav.value : prevNav.value
    if (target) applyNav(target)
  }

  function onTabKey(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement).tagName
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return
    if ((e.target as HTMLElement).isContentEditable) return
    if (e.key === 'j') navigate(-1)
    else if (e.key === 'k') navigate(1)
  }

  function syncFromRoute() {
    const resolved = resolveTabFromQuery(
      route.query.tab as string | undefined,
      route.query.section as string | undefined,
      tabs.value,
    )
    activeTab.value = resolved.tab
    activeSection.value = resolved.section
  }

  watch(activeTab, (tab, prev) => {
    if (tab === prev) return
    const sections = sectionsForTab(tab)
    if (!sections) {
      activeSection.value = null
      return
    }
    if (!activeSection.value || !sections.includes(activeSection.value)) {
      activeSection.value = sections[0]
    }
  })

  watch([activeTab, activeSection], ([tab, section]) => {
    const query: Record<string, string> = { ...route.query as Record<string, string>, tab }
    if (section) query.section = section
    else delete query.section
    router.replace({ query })
  })

  watch(tabs, (list) => {
    if (!list.includes(activeTab.value)) {
      applyNav({ tab: 'Overview', section: null })
    } else {
      const sections = sectionsForTab(activeTab.value)
      if (sections && (!activeSection.value || !sections.includes(activeSection.value))) {
        activeSection.value = sections[0]
      }
    }
  })

  watch(
    () => route.query.tab,
    () => syncFromRoute(),
  )

  return {
    activeTab,
    activeSection,
    activeChapterIndex,
    chapterPositionLabel,
    prevNav,
    nextNav,
    prevChapterLabel,
    nextChapterLabel,
    goToChapter,
    navigate,
    onTabKey,
    syncFromRoute,
  }
}
