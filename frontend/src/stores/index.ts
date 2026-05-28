import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    appName: import.meta.env.VITE_APP_NAME as string ?? 'Atlas Insight',
  }),
})
