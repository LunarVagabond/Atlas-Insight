<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const isDark = ref(false)

function applyTheme(dark: boolean) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  localStorage.setItem('theme', dark ? 'dark' : 'light')
}

function toggleTheme() {
  const bg = getComputedStyle(document.documentElement)
    .getPropertyValue('--color-bg').trim() || '#ffffff'
  const overlay = document.createElement('div')
  overlay.className = 'theme-peel-overlay'
  overlay.style.background = bg
  document.body.appendChild(overlay)

  isDark.value = !isDark.value
  applyTheme(isDark.value)

  requestAnimationFrame(() => {
    overlay.classList.add('theme-peel-overlay--active')
    overlay.addEventListener('animationend', () => overlay.remove(), { once: true })
  })
}

onMounted(async () => {
  const saved = localStorage.getItem('theme')
  isDark.value = saved === 'dark'
  applyTheme(isDark.value)
  await authStore.fetchMe()
  // Strip the ?login=success param allauth adds after OAuth redirect
  if (window.location.search.includes('login=success')) {
    router.replace({ query: {} })
  }
})

const menuOpen = ref(false)
</script>

<template>
  <div class="page">
    <nav class="navbar">
      <RouterLink to="/" class="navbar__brand">
        Atlas <span>Insight</span>
      </RouterLink>
      <div class="navbar__spacer" />
      <div class="navbar__nav-links">
        <RouterLink to="/runs" class="navbar__nav-link">Browse</RouterLink>
        <RouterLink to="/spotlight" class="navbar__nav-link">Spotlight</RouterLink>
        <RouterLink v-if="authStore.isAuthenticated" to="/dashboard" class="navbar__nav-link">My Analyses</RouterLink>
        <RouterLink to="/about" class="navbar__nav-link">About</RouterLink>
        <RouterLink v-if="authStore.user?.is_staff || authStore.user?.is_superuser" to="/admin" class="navbar__nav-link navbar__nav-link--admin">Ops</RouterLink>
      </div>
      <div class="navbar__actions">
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'">
          {{ isDark ? '☀️' : '🌙' }}
        </button>

        <!-- Unauthenticated -->
        <button
          v-if="!authStore.loading && !authStore.isAuthenticated"
          class="btn btn--primary btn--sm navbar__login"
          @click="authStore.loginWithGithub()"
        >
          <svg class="navbar__github-icon" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
              0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
              -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87
              2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
              0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82
              .64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82
              2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15
              0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
              0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
          </svg>
          Login with GitHub
        </button>

        <!-- Authenticated -->
        <div v-else-if="authStore.isAuthenticated" class="navbar__user" @click="menuOpen = !menuOpen">
          <img
            v-if="authStore.user?.avatar_url"
            :src="authStore.user.avatar_url"
            :alt="authStore.displayName"
            class="navbar__avatar"
          />
          <span class="navbar__username">{{ authStore.displayName }}</span>
          <span class="navbar__chevron">▾</span>

          <div v-if="menuOpen" class="navbar__dropdown">
            <RouterLink to="/settings" class="navbar__dropdown-item" @click="menuOpen = false">
              Settings
            </RouterLink>
            <button class="navbar__dropdown-item" @click="authStore.logout(); menuOpen = false">
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
    <div class="page__main">
      <RouterView />
    </div>
    <footer class="app-footer">
      © {{ new Date().getFullYear() }} Lunar Vagabond. All rights reserved.
      <span class="app-footer__sep">·</span>
      <a href="https://ko-fi.com/chrisconlon" target="_blank" rel="noopener noreferrer" class="app-footer__kofi">☕ Buy me a coffee</a>
    </footer>
  </div>
</template>
