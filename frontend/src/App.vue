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
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'">
          {{ isDark ? '☀️' : '🌙' }}
        </button>
      </div>
    </nav>
    <div class="page__main">
      <RouterView />
    </div>
    <footer class="app-footer">
      © {{ new Date().getFullYear() }} Lunar Vagabond. All rights reserved.
    </footer>
  </div>
</template>
