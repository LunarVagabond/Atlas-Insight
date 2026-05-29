<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import LoadingSpinner from '../components/ui/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()

onMounted(async () => {
  const { owner, name } = route.params as { owner: string; name: string }
  try {
    const { data } = await axios.get(`/api/v1/repositories/by-slug/${owner}/${name}`)
    router.replace(`/results/${data.run_id}`)
  } catch {
    router.replace('/')
  }
})
</script>

<template>
  <div style="display:flex;justify-content:center;padding:4rem">
    <LoadingSpinner size="lg" label="Loading repository…" />
  </div>
</template>
