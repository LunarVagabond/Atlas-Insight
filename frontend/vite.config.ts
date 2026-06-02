import { execSync } from 'child_process'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { version } from './package.json'

const gitSha = (() => {
  try {
    return execSync('git rev-parse --short HEAD').toString().trim()
  } catch {
    return 'unknown'
  }
})()

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version),
    __GIT_SHA__: JSON.stringify(gitSha),
  },
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  server: {
    port: 4501,
    fs: { strict: false },
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
