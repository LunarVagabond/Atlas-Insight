<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTokenStore } from '../stores/tokens'
import { useAuthStore } from '../stores/auth'
import AppCard from '../components/ui/AppCard.vue'
import AppButton from '../components/ui/AppButton.vue'

const tokenStore = useTokenStore()
const authStore = useAuthStore()

const newTokenName = ref('')
const creating = ref(false)
const createError = ref<string | null>(null)
const copiedToken = ref(false)

onMounted(() => {
  if (authStore.isAuthenticated) tokenStore.fetchTokens()
})

async function handleCreate() {
  if (!newTokenName.value.trim()) return
  createError.value = null
  creating.value = true
  try {
    await tokenStore.createToken(newTokenName.value.trim())
    newTokenName.value = ''
    copiedToken.value = false
  } catch (e: any) {
    createError.value = e?.response?.data?.detail ?? 'Failed to create token'
  } finally {
    creating.value = false
  }
}

async function copyToken(token: string) {
  await navigator.clipboard.writeText(token).catch(() => {})
  copiedToken.value = true
  setTimeout(() => { copiedToken.value = false }, 2000)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="settings-view">
    <div class="settings-view__header">
      <h1 class="settings-view__title">Settings</h1>
    </div>

    <div v-if="!authStore.isAuthenticated" class="empty-state">
      Sign in to manage your API tokens.
    </div>

    <template v-else>
      <!-- New token banner -->
      <div v-if="tokenStore.newToken" class="settings-token-reveal">
        <div class="settings-token-reveal__alert">
          <strong>Token created — copy it now.</strong> It won't be shown again.
        </div>
        <div class="settings-token-reveal__row">
          <code class="settings-token-reveal__value">{{ tokenStore.newToken.token }}</code>
          <AppButton variant="secondary" @click="copyToken(tokenStore.newToken!.token)">
            {{ copiedToken ? '✓ Copied' : 'Copy' }}
          </AppButton>
          <AppButton variant="secondary" @click="tokenStore.clearNewToken()">Dismiss</AppButton>
        </div>
        <p class="settings-token-reveal__usage">
          Use as: <code>Authorization: Bearer &lt;token&gt;</code>
        </p>
      </div>

      <AppCard class="settings-section">
        <h2 class="settings-section__title">API Tokens</h2>
        <p class="settings-section__desc">
          Personal tokens let you trigger scans from CI pipelines or scripts via the
          <code>POST /api/v1/repositories/analyze</code> endpoint.
        </p>

        <!-- Generate form -->
        <form class="settings-token-form" @submit.prevent="handleCreate">
          <input
            v-model="newTokenName"
            class="settings-token-form__input"
            placeholder="Token name (e.g. CI deploy)"
            maxlength="100"
            :disabled="creating"
          />
          <AppButton type="submit" :disabled="creating || !newTokenName.trim()">
            {{ creating ? 'Generating…' : 'Generate Token' }}
          </AppButton>
        </form>
        <p v-if="createError" class="settings-token-form__error">{{ createError }}</p>

        <!-- Token list -->
        <div v-if="tokenStore.loading" class="settings-token-list__empty">Loading tokens…</div>
        <div v-else-if="!tokenStore.tokens.length" class="settings-token-list__empty">
          No active tokens. Generate one above.
        </div>
        <table v-else class="data-table settings-token-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Created</th>
              <th>Last used</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="token in tokenStore.tokens" :key="token.id">
              <td>{{ token.name }}</td>
              <td>{{ formatDate(token.created_at) }}</td>
              <td>{{ token.last_used_at ? formatDate(token.last_used_at) : 'Never' }}</td>
              <td>
                <AppButton variant="secondary" @click="tokenStore.revokeToken(token.id)" style="font-size:0.8rem;padding:3px 10px;color:var(--color-error,#e53935)">
                  Revoke
                </AppButton>
              </td>
            </tr>
          </tbody>
        </table>
      </AppCard>
    </template>
  </div>
</template>
