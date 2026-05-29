<script setup lang="ts">
import { ref } from 'vue'
import AppButton from '../ui/AppButton.vue'

const emit = defineEmits<{ submitted: [url: string, pat?: string] }>()
defineProps<{ loading?: boolean; error?: string | null }>()

const url = ref('')
const localError = ref('')
const isPrivate = ref(false)
const pat = ref('')

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
  if (isPrivate.value && !pat.value.trim()) {
    localError.value = 'Please enter a Personal Access Token for private repos'
    return
  }
  emit('submitted', trimmed, isPrivate.value && pat.value.trim() ? pat.value.trim() : undefined)
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

    <label class="url-form__private-toggle">
      <input type="checkbox" v-model="isPrivate" :disabled="loading" />
      Private repository (requires PAT)
    </label>

    <div v-if="isPrivate" class="url-form__input-row" style="margin-top:0.5rem">
      <input
        v-model="pat"
        type="password"
        class="url-form__input"
        placeholder="GitHub Personal Access Token (repo scope)"
        :disabled="loading"
        autocomplete="off"
      />
    </div>

    <p v-if="localError || error" class="url-form__error">{{ localError || error }}</p>
  </form>
</template>
