import { defineStore } from 'pinia'
import axios from 'axios'

export interface AuthUser {
  id: number
  username: string
  email: string
  github_login: string
  avatar_url: string
  github_connected: boolean
  is_staff: boolean
  is_superuser: boolean
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as AuthUser | null,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => state.user !== null,
    displayName: (state) => state.user?.github_login || state.user?.username || '',
  },

  actions: {
    async fetchMe() {
      this.loading = true
      try {
        const { data } = await axios.get('/api/v1/auth/me')
        this.user = data
      } catch {
        this.user = null
      } finally {
        this.loading = false
      }
    },

    async logout() {
      try {
        await axios.post('/api/v1/auth/logout')
      } finally {
        this.user = null
      }
    },

    loginWithGithub() {
      window.location.href = '/accounts/github/login/'
    },

    connectGithub() {
      window.location.href = '/accounts/github/login/?process=connect&next=' + encodeURIComponent(window.location.pathname)
    },
  },
})
