import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as Sentry from '@sentry/vue'

import App from './App.vue'
import router from './router'
import './styles/main.scss'

const app = createApp(App)

const sentryDsn = import.meta.env.VITE_SENTRY_DSN
const sentryService = import.meta.env.VITE_SERVICE_NAME || 'atlas-frontend-vue'

if (sentryDsn) {
	Sentry.init({
		app,
		dsn: sentryDsn,
		environment: import.meta.env.MODE,
		tracesSampleRate: 0.1,
		beforeSend(event) {
			const tags = { ...(event.tags || {}) }
			tags.service = sentryService
			event.tags = tags

			const contexts = { ...(event.contexts || {}) }
			const service = { ...(contexts.service || {}) }
			service.name = sentryService
			contexts.service = service
			event.contexts = contexts

			return event
		},
	})

	Sentry.setTag('service', sentryService)
}

app.use(createPinia())
app.use(router)
app.mount('#app')
