<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="not-found">
    <div class="not-found__code" aria-hidden="true">404</div>
    <h1 class="not-found__title">Page not found</h1>
    <p class="not-found__message">That URL doesn't exist. Try searching for a repository or go back home.</p>
    <div class="not-found__actions">
      <button class="btn btn--primary" @click="router.push('/')">← Home</button>
      <button class="btn btn--secondary" @click="router.push('/runs')">Browse analyses</button>
    </div>
  </div>
</template>
