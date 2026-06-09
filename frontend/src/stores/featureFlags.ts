import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export const useFeatureFlagsStore = defineStore('featureFlags', () => {
  const loaded = ref(false)
  const spotlight = ref(true)
  const trending = ref(true)

  async function fetchFlags() {
    try {
      const { data } = await axios.get<{ spotlight: boolean; trending: boolean }>(
        '/api/v1/repositories/features',
      )
      spotlight.value = data.spotlight
      trending.value = data.trending
    } catch {
      spotlight.value = true
      trending.value = true
    } finally {
      loaded.value = true
    }
  }

  return { loaded, spotlight, trending, fetchFlags }
})
