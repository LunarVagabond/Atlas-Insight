<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{
  result: Record<string, any>
  repoOwner: string
  repoName: string
  onStartReading: () => void
}>()

function pluralize(n: number, word: string) {
  return `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`
}

function ageFromDate(isoDate: string): string {
  const created = new Date(isoDate)
  const years = Math.floor((Date.now() - created.getTime()) / (1000 * 60 * 60 * 24 * 365))
  if (years < 1) return 'less than a year old'
  return `${years} year${years === 1 ? '' : 's'} old`
}

const narrative = computed(() => {
  const meta: Record<string, any> = props.result.github_meta ?? {}
  const cls: Record<string, any> = props.result.classification ?? {}
  const commits: Record<string, any> = props.result.commits ?? {}
  const structure: Record<string, any> = props.result.structure ?? {}

  const name = `${props.repoOwner}/${props.repoName}`
  const techStack: string[] = structure.tech_stack ?? []
  const desc = meta.github_description ? (meta.github_description as string).replace(/\.$/, '') : null
  const health = cls.project_health?.label ?? null
  const difficulty = cls.contribution_difficulty?.label ?? null
  const contributors = commits.total_contributors ?? 0
  const totalCommits = commits.total_commits ?? 0
  const age = meta.created_at ? ageFromDate(meta.created_at as string) : null
  const busFactor = structure.bus_factor ?? null

  // Build a meaningful project-type label from the tech stack
  const hasTauri = techStack.includes('Tauri')
  const hasVue = techStack.includes('Vue')
  const hasReact = techStack.includes('React')
  const hasNextjs = techStack.includes('Next.js')
  const hasNuxt = techStack.includes('Nuxt')
  const primaryLang = meta.primary_language as string | null

  let projectType: string
  if (hasTauri) {
    const ui = hasVue ? 'Vue' : hasReact ? 'React' : primaryLang ?? 'web'
    projectType = `${ui} + Tauri desktop app`
  } else if (hasNextjs) {
    projectType = 'Next.js app'
  } else if (hasNuxt) {
    projectType = 'Nuxt app'
  } else if (hasVue) {
    projectType = 'Vue app'
  } else if (hasReact) {
    projectType = 'React app'
  } else if (primaryLang) {
    projectType = `${primaryLang} repository`
  } else {
    projectType = 'repository'
  }

  const sentences: string[] = []

  // Sentence 1: identity
  let s1 = `**${name}** is a ${projectType}`
  if (desc) s1 += ` — ${desc}`
  if (age) s1 += `, ${age}`
  if (contributors > 0 && totalCommits > 0) {
    s1 += `, with ${pluralize(totalCommits, 'commit')} from ${pluralize(contributors, 'contributor')}`
  }
  sentences.push(s1 + '.')

  // Sentence 2: health & contribution posture
  if (health || difficulty) {
    let s2 = ''
    if (health) s2 += `It scores **${health}** on project health`
    if (difficulty) s2 += `${health ? ' and is rated ' : 'Contributions are rated '}**${difficulty}** for new contributors`
    sentences.push(s2 + '.')
  }

  // Sentence 3: bus factor signal
  if (busFactor !== null) {
    if (contributors === 1) {
      // Solo project — bus factor is inherently 1, not a risk signal
    } else if (busFactor <= 1) {
      sentences.push('Knowledge is concentrated in very few contributors — high bus factor risk.')
    } else if (busFactor <= 3) {
      sentences.push(`The bus factor is **${busFactor}** — a small core team carries most of the knowledge.`)
    } else {
      sentences.push(`With a bus factor of **${busFactor}**, knowledge is well-distributed across the team.`)
    }
  }

  return sentences
})
</script>

<template>
  <div class="repo-narrative">
    <div class="repo-narrative__body">
      <p v-for="(sentence, i) in narrative" :key="i" class="repo-narrative__sentence" v-html="sentence.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')" />
    </div>
    <div class="repo-narrative__cta">
      <button class="btn btn--primary repo-narrative__start" @click="onStartReading">
        Start Reading →
      </button>
    </div>
  </div>
</template>
