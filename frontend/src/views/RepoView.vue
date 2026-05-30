<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const errorMsg = ref<string | null>(null)

onMounted(async () => {
  const { owner, name } = route.params as { owner: string; name: string }
  try {
    const { data } = await axios.get(`/api/v1/repositories/by-slug/${owner}/${name}`)
    router.replace(`/results/${data.run_id}`)
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } }).response?.status
    errorMsg.value = status === 404
      ? `Repository "${owner}/${name}" not found. It may not have been analyzed yet.`
      : 'Failed to load repository. Please try again.'
  }
})
</script>

<template>
  <div style="display:flex;justify-content:center;padding:4rem">
    <div v-if="errorMsg" class="analysis-error-card">
      <div class="analysis-error-card__icon">✕</div>
      <h2 class="analysis-error-card__title">Repository Not Found</h2>
      <p class="analysis-error-card__message">{{ errorMsg }}</p>
      <div class="analysis-error-card__actions">
        <a href="/" class="btn btn--primary">← New Analysis</a>
      </div>
    </div>
    <LoadingSpinner v-else size="lg" label="Loading repository…" />
  </div>
</template>
