<script setup lang="ts">
import { useRouter } from 'vue-router'
import URLInputForm from '../components/analysis/URLInputForm.vue'
import { useAnalysisStore } from '../stores/analysis'

const router = useRouter()
const store = useAnalysisStore()

async function handleSubmit(url: string) {
  try {
    const runId = await store.submitUrl(url)
    router.push(`/results/${runId}`)
  } catch {
    // error shown in form
  }
}
</script>

<template>
  <main class="hero">
    <h1 class="hero__title">Repository <span>Archaeology</span></h1>
    <p class="hero__subtitle">
      Submit any public GitHub repository and get a deep analysis of its commit history,
      architecture, dependencies, and health signals.
    </p>
    <URLInputForm
      :loading="store.status === 'submitting'"
      :error="store.error"
      @submitted="handleSubmit"
    />
  </main>
</template>
