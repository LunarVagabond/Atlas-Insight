<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

const isDark = ref(false)

function applyTheme(dark: boolean) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  localStorage.setItem('theme', dark ? 'dark' : 'light')
}

function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme(isDark.value)
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  isDark.value = saved === 'dark'
  applyTheme(isDark.value)
})
</script>

<template>
  <div class="page">
    <nav class="navbar">
      <RouterLink to="/" class="navbar__brand">
        Atlas <span>Insight</span>
      </RouterLink>
      <div class="navbar__spacer" />
      <div class="navbar__actions">
        <RouterLink to="/runs" class="btn btn--secondary" style="font-size:0.8125rem;padding:6px 12px">
          Browse Runs
        </RouterLink>
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'">
          {{ isDark ? '☀️' : '🌙' }}
        </button>
      </div>
    </nav>
    <RouterView />
  </div>
</template>
