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
    allowedHosts: [
      'atlas.dsyndicate.dev',
      'ai-api.dsyndicate.dev',
      'ai-flower.dsyndicate.dev',
      'localhost',
      '127.0.0.1',
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:4500',
        changeOrigin: true,
      },
      '/accounts': {
        target: 'http://localhost:4500',
        changeOrigin: true,
      },
    },
  },
})
