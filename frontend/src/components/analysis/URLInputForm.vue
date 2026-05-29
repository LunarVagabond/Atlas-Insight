<script setup lang="ts">
import { ref } from 'vue'
import AppButton from '../ui/AppButton.vue'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits<{ submitted: [url: string] }>()
defineProps<{ loading?: boolean; error?: string | null }>()

const auth = useAuthStore()
const url = ref('')
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
  emit('submitted', trimmed)
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

    <p v-if="auth.isAuthenticated" class="url-form__auth-note">
      Logged in as <strong>{{ auth.displayName }}</strong> — private repos you have access to are supported automatically.
    </p>

    <p v-if="localError || error" class="url-form__error">{{ localError || error }}</p>
  </form>
</template>
