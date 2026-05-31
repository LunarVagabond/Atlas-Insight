import { defineStore } from 'pinia'
import axios from 'axios'

export interface APITokenItem {
  id: string
  name: string
  created_at: string
  last_used_at: string | null
}

export interface NewTokenResult extends APITokenItem {
  token: string
}

export const useTokenStore = defineStore('tokens', {
  state: () => ({
    tokens: [] as APITokenItem[],
    loading: false,
    newToken: null as NewTokenResult | null,
  }),

  actions: {
    async fetchTokens() {
      this.loading = true
      try {
        const { data } = await axios.get('/api/v1/auth/tokens')
        this.tokens = data
      } finally {
        this.loading = false
      }
    },

    async createToken(name: string): Promise<NewTokenResult> {
      const { data } = await axios.post('/api/v1/auth/tokens', { name })
      this.newToken = data
      this.tokens.unshift({ id: data.id, name: data.name, created_at: data.created_at, last_used_at: null })
      return data
    },

    async revokeToken(id: string) {
      await axios.delete(`/api/v1/auth/tokens/${id}`)
      this.tokens = this.tokens.filter(t => t.id !== id)
    },

    clearNewToken() {
      this.newToken = null
    },
  },
})
