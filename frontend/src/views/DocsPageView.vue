<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import axios from 'axios'

const route = useRoute()

const title = ref('')
const html = ref('')
const loading = ref(true)
const error = ref<string | null>(null)

async function load(slug: string) {
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get(`/api/v1/docs/${slug}`)
    title.value = data.title
    const raw = marked.parse(data.content, { async: false }) as string
    html.value = DOMPurify.sanitize(raw)
  } catch {
    error.value = 'This page could not be loaded.'
  } finally {
    loading.value = false
  }
}

onMounted(() => load(route.params.slug as string))
watch(() => route.params.slug, (slug) => load(slug as string))
</script>

<template>
  <div class="docs-page">
    <div v-if="loading" class="docs-page__loading">Loading…</div>
    <div v-else-if="error" class="docs-page__error">{{ error }}</div>
    <article v-else class="docs-page__article prose" v-html="html" />
  </div>
</template>
