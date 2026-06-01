export const BACKEND_FRAMEWORKS = new Set([
  // Python
  'Django', 'Flask', 'FastAPI', 'Starlette', 'Tornado', 'Bottle', 'Sanic',
  'Litestar', 'Falcon', 'aiohttp', 'Robyn', 'BlackSheep', 'Quart', 'Masonite',
  // Ruby
  'Rails', 'Sinatra', 'Hanami', 'Grape', 'Padrino', 'Roda',
  // Go
  'Gin', 'Echo', 'Fiber', 'Gorilla Mux', 'Chi', 'Beego', 'Buffalo', 'Iris',
  'Negroni', 'Go kit',
  // Rust
  'Actix', 'Rocket', 'Axum', 'Warp', 'Poem', 'Salvo', 'Tide', 'ntex',
  // Java / Kotlin / JVM
  'Spring Boot', 'Spring', 'Ktor', 'Micronaut', 'Quarkus', 'Dropwizard',
  'Javalin', 'Helidon', 'Vert.x', 'http4k', 'Play Framework', 'Akka HTTP',
  'ZIO HTTP', 'http4s',
  // PHP
  'Laravel', 'Symfony', 'Slim', 'CakePHP', 'Yii2', 'CodeIgniter',
  'Phalcon', 'Laminas', 'Lumen', 'Spiral',
  // Elixir
  'Phoenix', 'Plug',
  // Haskell
  'Servant', 'Yesod', 'Scotty',
  // JS/TS backend
  'Express', 'Fastify', 'Koa', 'Hono', 'NestJS', 'AdonisJS', 'Feathers',
  'Sails', 'Polka', 'H3', 'Elysia', 'Hapi', 'Restify', 'LoopBack',
  // CMS / BaaS as backend
  'Strapi', 'Directus', 'Payload CMS', 'Ghost',
  // Dart
  'Shelf', 'Serverpod',
])

export const FRONTEND_FRAMEWORKS = new Set([
  'Vue', 'React', 'Svelte', 'Angular', 'Solid', 'Preact', 'Lit',
  'Alpine.js', 'Stimulus', 'jQuery', 'HTMX', 'Qwik', 'Marko',
  'Mithril', 'Inferno', 'Stencil', 'Hyperapp',
  // Meta-frameworks
  'Next.js', 'Nuxt', 'Remix', 'SvelteKit', 'Gatsby', 'Astro',
  'Hydrogen', 'TanStack Start', 'Analog',
])

export const META_FRAMEWORKS = new Set([
  'Next.js', 'Nuxt', 'Remix', 'SvelteKit', 'Gatsby', 'Astro',
  'Hydrogen', 'TanStack Start', 'Analog',
])

export const DESKTOP_FRAMEWORKS = new Set(['Tauri', 'Electron', 'Neutralino', 'NativeScript'])

export const MOBILE_FRAMEWORKS = new Set(['React Native', 'Expo', 'Ionic', 'Capacitor', 'Flutter'])

export const DB_TOOLS = new Set([
  'Prisma', 'TypeORM', 'Sequelize', 'Mongoose', 'Drizzle', 'MikroORM',
  'Objection', 'Knex', 'SQLAlchemy', 'Tortoise ORM', 'Peewee', 'Pony ORM',
  'MongoEngine', 'Motor', 'Alembic', 'GORM', 'Ent', 'Diesel', 'SeaORM',
  'SQLx', 'Hibernate', 'Exposed', 'jOOQ', 'Dapper', 'Entity Framework',
  'Databases', 'node-postgres',
])

export const QUEUE_TOOLS = new Set([
  'Celery', 'RQ', 'Dramatiq', 'Huey', 'Arq', 'APScheduler',
  'BullMQ', 'Bull', 'Agenda', 'Sidekiq', 'Oban', 'Broadway',
])

export const TESTING_TOOLS = new Set([
  'pytest', 'Hypothesis', 'Locust', 'factory_boy',
  'Jest', 'Vitest', 'Mocha', 'Jasmine', 'Ava',
  'Playwright', 'Cypress', 'Puppeteer', 'Testing Library',
  'Chai', 'Sinon', 'Supertest', 'Storybook', 'k6',
  'RSpec', 'Capybara', 'Testify', 'JUnit', 'Mockito',
])

export const STATE_TOOLS = new Set([
  'Pinia', 'Redux', 'Redux Toolkit', 'Zustand', 'Jotai', 'Recoil',
  'MobX', 'Valtio', 'XState', 'Nanostores', 'Effector', 'Legend State',
  'RxJS', '@ngrx',
])

export const BUNDLER_NOISE = new Set([
  'Vite', 'Webpack', 'Turbopack', 'Parcel', 'esbuild', 'Rollup', 'Rspack', 'tsup',
])

export function buildProjectType(techStack: string[], primaryLang: string | null): string {
  const backends = techStack.filter(t => BACKEND_FRAMEWORKS.has(t))
  const frontends = techStack.filter(t => FRONTEND_FRAMEWORKS.has(t))
  const desktops = techStack.filter(t => DESKTOP_FRAMEWORKS.has(t))
  const mobiles = techStack.filter(t => MOBILE_FRAMEWORKS.has(t))

  const frontendLabel = frontends.find(f => META_FRAMEWORKS.has(f)) ?? frontends[0] ?? null
  const backendLabel = backends[0] ?? null
  const desktopLabel = desktops[0] ?? null
  const mobileLabel = mobiles[0] ?? null

  if (desktopLabel) {
    const ui = frontendLabel ?? primaryLang ?? 'web'
    return `${ui} + ${desktopLabel} desktop app`
  }
  if (mobileLabel && !backendLabel) {
    return `${mobileLabel} app`
  }
  if (backendLabel && frontendLabel) {
    return `${backendLabel} + ${frontendLabel} full-stack app`
  }
  if (backendLabel) {
    return `${backendLabel} project`
  }
  if (frontendLabel) {
    return `${frontendLabel} app`
  }
  if (primaryLang) {
    return `${primaryLang} repository`
  }
  return 'repository'
}

export function buildStackSentence(techStack: string[]): string | null {
  const notable = techStack.filter(t => !BUNDLER_NOISE.has(t))
  if (notable.length < 2) return null

  const parts: string[] = []
  const backends = notable.filter(t => BACKEND_FRAMEWORKS.has(t))
  const frontends = notable.filter(t => FRONTEND_FRAMEWORKS.has(t))
  const dbs = notable.filter(t => DB_TOOLS.has(t))
  const queues = notable.filter(t => QUEUE_TOOLS.has(t))
  const testing = notable.filter(t => TESTING_TOOLS.has(t))
  const state = notable.filter(t => STATE_TOOLS.has(t))
  const mobiles = notable.filter(t => MOBILE_FRAMEWORKS.has(t))
  const desktops = notable.filter(t => DESKTOP_FRAMEWORKS.has(t))

  if (backends.length) parts.push(backends.join(' + '))
  if (frontends.length) parts.push(frontends.join(' + '))
  if (mobiles.length && !frontends.length) parts.push(mobiles.join(' + '))
  if (desktops.length && !backends.length && !frontends.length) parts.push(desktops[0])
  if (dbs.length) parts.push(dbs.slice(0, 2).join(' + '))
  if (queues.length) parts.push(queues.slice(0, 2).join(' + '))
  if (state.length) parts.push(state[0])
  if (testing.length) parts.push(`${testing.slice(0, 2).join(' + ')} for testing`)

  if (parts.length < 2) return null
  return `Built with ${parts.join(', ')}.`
}
