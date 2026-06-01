<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import AppButton from '../ui/AppButton.vue'
import { useAuthStore } from '../../stores/auth'

const props = withDefaults(defineProps<{ loading?: boolean; error?: string | null; initialUrl?: string }>(), {
  loading: false,
  error: null,
  initialUrl: '',
})

const emit = defineEmits<{ submitted: [url: string, pat?: string] }>()

const auth = useAuthStore()
const url = ref(props.initialUrl || '')
const pat = ref('')
const showPat = ref(false)
const localError = ref('')

interface GhRepo { full_name: string; html_url: string; private: boolean }
const userRepos = ref<GhRepo[]>([])
const reposLoading = ref(false)
const showDropdown = ref(false)

const filteredRepos = computed(() => {
  const q = url.value.trim().toLowerCase()
  if (!q) return userRepos.value.slice(0, 8)
  return userRepos.value.filter(r =>
    r.full_name.toLowerCase().includes(q) || r.html_url.toLowerCase().includes(q)
  ).slice(0, 8)
})

const canShowDropdown = computed(() =>
  auth.isAuthenticated && auth.user?.github_connected && showDropdown.value && filteredRepos.value.length > 0
)

async function fetchUserRepos() {
  if (!auth.isAuthenticated || !auth.user?.github_connected) return
  if (userRepos.value.length) return
  reposLoading.value = true
  try {
    const { data } = await axios.get('/api/v1/repositories/my-repos')
    userRepos.value = data
  } catch {
    // silently fail — dropdown just won't show
  } finally {
    reposLoading.value = false
  }
}

function onFocus() {
  showDropdown.value = true
  fetchUserRepos()
}

function selectRepo(repo: GhRepo) {
  url.value = repo.html_url
  showDropdown.value = false
}

function onClickOutside(e: MouseEvent) {
  const form = document.querySelector('.url-form')
  if (form && !form.contains(e.target as Node)) {
    showDropdown.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))

const GITHUB_RE = /^https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?$/

function submit() {
  localError.value = ''
  showDropdown.value = false
  const trimmed = url.value.trim()
  if (!trimmed) {
    localError.value = 'Please enter a GitHub URL'
    return
  }
  if (!GITHUB_RE.test(trimmed)) {
    localError.value = 'Must be a valid GitHub repository URL (e.g. https://github.com/owner/repo)'
    return
  }
  emit('submitted', trimmed, pat.value.trim() || undefined)
}

function togglePat() {
  showPat.value = !showPat.value
  if (!showPat.value) pat.value = ''
}
</script>

<template>
  <form class="url-form" @submit.prevent="submit">
    <div class="url-form__input-row" style="position: relative">
      <input
        v-model="url"
        type="url"
        class="url-form__input"
        placeholder="https://github.com/owner/repository"
        :disabled="loading"
        autocomplete="off"
        spellcheck="false"
        @focus="onFocus"
        @input="showDropdown = true"
      />
      <AppButton type="submit" size="lg" :loading="loading">
        Analyze
      </AppButton>

      <!-- Repo dropdown -->
      <div v-if="canShowDropdown" class="url-form__repo-dropdown">
        <div
          v-for="repo in filteredRepos"
          :key="repo.full_name"
          class="url-form__repo-option"
          @mousedown.prevent="selectRepo(repo)"
        >
          <span class="url-form__repo-name">{{ repo.full_name }}</span>
          <span v-if="repo.private" class="url-form__repo-private">private</span>
        </div>
      </div>
    </div>

    <!-- Options strip — visually attached to input -->
    <div class="url-form__options-strip">
      <p v-if="auth.isAuthenticated && auth.user?.github_connected" class="url-form__auth-note">
        <strong>{{ auth.displayName }}</strong> — private repos supported.
      </p>
      <p v-else-if="auth.isAuthenticated && !auth.user?.github_connected" class="url-form__auth-note url-form__auth-note--warn">
        GitHub not connected.
        <button type="button" class="url-form__text-btn" @click="auth.connectGithub()">Connect →</button>
      </p>
      <div class="url-form__options-btns">
        <button
          type="button"
          class="url-form__opt-btn"
          :class="{ 'url-form__opt-btn--active': showPat }"
          @click="togglePat"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M4 8a4 4 0 1 1 8 0A4 4 0 0 1 4 8zm4-5a5 5 0 1 0 2.546 9.31L13.854 15.6a.75.75 0 1 0 1.061-1.061l-2.903-2.903A5 5 0 0 0 8 3z"/></svg>
          PAT
        </button>
      </div>
    </div>

    <div v-if="showPat" class="url-form__pat-panel">
      <p class="url-form__pat-why">
        Required when your GitHub OAuth app isn't approved by the repository's organization,
        or for fine-grained access control. Your token is used only for this request and never stored.
        <a
          href="https://github.com/settings/tokens/new?scopes=repo&description=Atlas+Insight"
          target="_blank"
          rel="noopener noreferrer"
          class="url-form__pat-link"
        >Create one on GitHub →</a>
      </p>
      <input
        v-model="pat"
        type="password"
        class="url-form__input url-form__pat-input"
        placeholder="ghp_••••••••••••••••••••••••••••••••••••••"
        autocomplete="off"
        spellcheck="false"
      />
    </div>

    <p v-if="localError || error" class="url-form__error">{{ localError || error }}</p>
  </form>
</template>
