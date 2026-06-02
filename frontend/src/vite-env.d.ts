/// <reference types="vite/client" />

declare const __APP_VERSION__: string
declare const __GIT_SHA__: string

interface ImportMetaEnv {
  readonly VITE_APP_NAME: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_PUBLIC_BASE_URL: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_SERVICE_NAME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
