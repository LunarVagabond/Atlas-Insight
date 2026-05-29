<script setup lang="ts">
import { ref } from 'vue'
import AppButton from '../ui/AppButton.vue'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits<{ submitted: [url: string, pat?: string] }>()
defineProps<{ loading?: boolean; error?: string | null }>()

const auth = useAuthStore()
const url = ref('')
const pat = ref('')
const showPat = ref(false)
const localError = ref('')

const GITHUB_RE = /^https?:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?$/

function submit() {
  localError.value = ''
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
    <div class="url-form__input-row">
      <input
        v-model="url"
        type="url"
        class="url-form__input"
        placeholder="https://github.com/owner/repository"
        :disabled="loading"
        autocomplete="off"
        spellcheck="false"
      />
      <AppButton type="submit" size="lg" :loading="loading">
        Analyze
      </AppButton>
    </div>

    <div class="url-form__meta">
      <p v-if="auth.isAuthenticated && auth.user?.github_connected" class="url-form__auth-note">
        Logged in as <strong>{{ auth.displayName }}</strong> — private repos accessible to your account are supported.
      </p>
      <p v-else-if="auth.isAuthenticated && !auth.user?.github_connected" class="url-form__auth-note url-form__auth-note--warn">
        GitHub not connected — private repos will fail.
        <button type="button" class="url-form__text-btn" @click="auth.connectGithub()">Connect GitHub</button>
      </p>

      <button
        type="button"
        class="url-form__pat-toggle"
        :class="{ 'url-form__pat-toggle--active': showPat }"
        @click="togglePat"
      >
        <span class="url-form__pat-toggle-icon">{{ showPat ? '−' : '+' }}</span>
        Personal Access Token
      </button>
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
