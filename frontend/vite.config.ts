import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  server: {
    port: 4501,
    proxy: {
      '/api': {
        target: 'http://localhost:4500',
        changeOrigin: true,
      },
    },
  },
})
