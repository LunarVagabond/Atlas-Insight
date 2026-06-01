export const KNOWN_FRAMEWORKS: Record<string, string> = {
  // ── Python ──────────────────────────────────────────────────────────────
  'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
  'starlette': 'Starlette', 'tornado': 'Tornado', 'bottle': 'Bottle',
  'sanic': 'Sanic', 'litestar': 'Litestar', 'falcon': 'Falcon',
  'aiohttp': 'aiohttp', 'robyn': 'Robyn', 'blacksheep': 'BlackSheep',
  'quart': 'Quart', 'masonite': 'Masonite',
  'sqlalchemy': 'SQLAlchemy', 'tortoise-orm': 'Tortoise ORM',
  'peewee': 'Peewee', 'mongoengine': 'MongoEngine', 'motor': 'Motor',
  'alembic': 'Alembic', 'celery': 'Celery', 'rq': 'RQ',
  'dramatiq': 'Dramatiq', 'huey': 'Huey', 'arq': 'Arq',
  'djangorestframework': 'DRF', 'django-ninja': 'Django Ninja',
  'graphene': 'Graphene', 'strawberry-graphql': 'Strawberry',
  'pytest': 'pytest', 'hypothesis': 'Hypothesis', 'locust': 'Locust',
  'numpy': 'NumPy', 'pandas': 'Pandas', 'scikit-learn': 'scikit-learn',
  'torch': 'PyTorch', 'tensorflow': 'TensorFlow', 'keras': 'Keras',
  'transformers': 'Hugging Face', 'langchain': 'LangChain',
  'llama-index': 'LlamaIndex', 'openai': 'OpenAI SDK',
  'anthropic': 'Anthropic SDK', 'streamlit': 'Streamlit',
  'gradio': 'Gradio', 'dash': 'Dash', 'polars': 'Polars',
  // ── Ruby ────────────────────────────────────────────────────────────────
  'rails': 'Rails', 'sinatra': 'Sinatra', 'hanami': 'Hanami',
  'grape': 'Grape', 'padrino': 'Padrino', 'roda': 'Roda',
  'sidekiq': 'Sidekiq', 'devise': 'Devise',
  // ── Go ──────────────────────────────────────────────────────────────────
  'gin-gonic/gin': 'Gin', 'labstack/echo': 'Echo', 'gofiber/fiber': 'Fiber',
  'gorilla/mux': 'Gorilla Mux', 'go-chi/chi': 'Chi', 'chi': 'Chi',
  'beego/beego': 'Beego', 'gobuffalo/buffalo': 'Buffalo',
  'go-iris/iris': 'Iris', 'gorm.io/gorm': 'GORM', 'ent/ent': 'Ent',
  // ── Rust ────────────────────────────────────────────────────────────────
  'actix-web': 'Actix', 'rocket': 'Rocket', 'axum': 'Axum', 'warp': 'Warp',
  'poem': 'Poem', 'salvo': 'Salvo', 'tauri': 'Tauri',
  '@tauri-apps/api': 'Tauri', 'diesel': 'Diesel', 'sea-orm': 'SeaORM',
  'sqlx': 'SQLx', 'tokio': 'Tokio', 'serde': 'Serde',
  'bevy': 'Bevy', 'leptos': 'Leptos', 'yew': 'Yew', 'dioxus': 'Dioxus',
  // ── Java / Kotlin ────────────────────────────────────────────────────────
  'spring-boot': 'Spring Boot', 'spring': 'Spring',
  'ktor': 'Ktor', 'micronaut': 'Micronaut', 'quarkus': 'Quarkus',
  'dropwizard': 'Dropwizard', 'javalin': 'Javalin', 'vertx': 'Vert.x',
  'hibernate': 'Hibernate', 'exposed': 'Exposed',
  // ── PHP ─────────────────────────────────────────────────────────────────
  'laravel/framework': 'Laravel', 'symfony/symfony': 'Symfony',
  'slim/slim': 'Slim', 'cakephp/cakephp': 'CakePHP',
  'yiisoft/yii2': 'Yii2', 'codeigniter4/framework': 'CodeIgniter',
  // ── Elixir ──────────────────────────────────────────────────────────────
  'phoenix': 'Phoenix', 'ecto': 'Ecto', 'oban': 'Oban',
  // ── Dart / Flutter ───────────────────────────────────────────────────────
  'flutter': 'Flutter', 'shelf': 'Shelf', 'serverpod': 'Serverpod',
  'flutter_bloc': 'flutter_bloc', 'riverpod': 'Riverpod',
  'provider': 'Provider', 'dio': 'Dio',
  // ── JS/TS frontend ───────────────────────────────────────────────────────
  'vue': 'Vue', 'react': 'React', 'svelte': 'Svelte',
  'solid-js': 'Solid', 'astro': 'Astro', '@angular/core': 'Angular',
  'preact': 'Preact', 'lit': 'Lit', 'alpinejs': 'Alpine.js',
  '@alpinejs/core': 'Alpine.js', '@hotwired/stimulus': 'Stimulus',
  'jquery': 'jQuery', 'htmx.org': 'HTMX', 'htmx': 'HTMX',
  '@builder.io/qwik': 'Qwik', 'qwik': 'Qwik',
  'marko': 'Marko', 'mithril': 'Mithril', 'inferno': 'Inferno',
  'stencil': 'Stencil',
  // JS/TS meta-frameworks
  'next': 'Next.js', 'nuxt': 'Nuxt', '@nuxt/core': 'Nuxt',
  'remix': 'Remix', '@sveltejs/kit': 'SvelteKit',
  'gatsby': 'Gatsby', '@shopify/hydrogen': 'Hydrogen',
  '@tanstack/start': 'TanStack Start', 'analog': 'Analog',
  // JS/TS backend
  'express': 'Express', 'fastify': 'Fastify', 'koa': 'Koa',
  'hono': 'Hono', '@nestjs/core': 'NestJS', 'nestjs': 'NestJS',
  '@adonisjs/core': 'AdonisJS', '@feathersjs/feathers': 'Feathers',
  'sails': 'Sails', 'polka': 'Polka', 'h3': 'H3', 'elysia': 'Elysia',
  '@hapi/hapi': 'Hapi', 'hapi': 'Hapi', 'restify': 'Restify',
  '@loopback/core': 'LoopBack', '@strapi/strapi': 'Strapi',
  'directus': 'Directus', 'payload': 'Payload CMS',
  // JS/TS ORMs / DB
  'prisma': 'Prisma', 'typeorm': 'TypeORM', 'sequelize': 'Sequelize',
  'mongoose': 'Mongoose', 'drizzle-orm': 'Drizzle',
  '@mikro-orm/core': 'MikroORM', 'mikro-orm': 'MikroORM',
  'objection': 'Objection', 'knex': 'Knex',
  // JS/TS GraphQL / API
  'graphql': 'GraphQL', '@trpc/server': 'tRPC', 'trpc': 'tRPC',
  '@grpc/grpc-js': 'gRPC', 'grpc': 'gRPC',
  '@apollo/server': 'Apollo Server', 'apollo-server': 'Apollo Server',
  '@apollo/client': 'Apollo Client', 'urql': 'URQL',
  // JS/TS state management
  'pinia': 'Pinia', 'redux': 'Redux', '@reduxjs/toolkit': 'Redux Toolkit',
  'zustand': 'Zustand', 'jotai': 'Jotai', 'recoil': 'Recoil',
  'mobx': 'MobX', 'valtio': 'Valtio', 'xstate': 'XState',
  '@xstate/react': 'XState', 'nanostores': 'Nanostores',
  'effector': 'Effector', '@legendapp/state': 'Legend State', 'rxjs': 'RxJS',
  // JS/TS UI / component libraries
  'tailwindcss': 'Tailwind', 'daisyui': 'DaisyUI', 'bootstrap': 'Bootstrap',
  'bulma': 'Bulma', '@mui/material': 'MUI',
  'antd': 'Ant Design', 'chakra-ui': 'Chakra UI', '@chakra-ui/react': 'Chakra UI',
  '@mantine/core': 'Mantine', '@headlessui/react': 'Headless UI',
  '@headlessui/vue': 'Headless UI', '@radix-ui/react-primitive': 'Radix UI',
  'vuetify': 'Vuetify', 'primevue': 'PrimeVue',
  'element-plus': 'Element Plus', 'naive-ui': 'Naive UI',
  'quasar': 'Quasar', '@quasar/app': 'Quasar', 'vant': 'Vant',
  'styled-components': 'Styled Components',
  '@emotion/react': 'Emotion', '@emotion/styled': 'Emotion',
  '@vanilla-extract/css': 'vanilla-extract',
  '@angular/material': 'Angular Material', 'primeng': 'PrimeNG',
  // JS/TS testing
  'jest': 'Jest', 'vitest': 'Vitest', 'mocha': 'Mocha',
  'jasmine': 'Jasmine', 'ava': 'Ava', '@playwright/test': 'Playwright',
  'playwright': 'Playwright', 'cypress': 'Cypress',
  'puppeteer': 'Puppeteer', '@testing-library/react': 'Testing Library',
  '@testing-library/vue': 'Testing Library', '@testing-library/dom': 'Testing Library',
  'chai': 'Chai', 'sinon': 'Sinon', '@storybook/react': 'Storybook',
  // JS/TS build / bundlers
  'vite': 'Vite', 'webpack': 'Webpack', 'turbopack': 'Turbopack',
  'parcel': 'Parcel', 'esbuild': 'esbuild', 'rollup': 'Rollup',
  '@rspack/core': 'Rspack', 'tsup': 'tsup', '@biomejs/biome': 'Biome',
  // JS/TS data fetching
  '@tanstack/react-query': 'TanStack Query', '@tanstack/vue-query': 'TanStack Query',
  'swr': 'SWR',
  // JS/TS auth
  'passport': 'Passport', 'next-auth': 'NextAuth', '@auth/core': 'Auth.js',
  '@clerk/nextjs': 'Clerk', '@clerk/clerk-react': 'Clerk', 'lucia': 'Lucia',
  // JS/TS realtime / messaging
  'socket.io': 'Socket.io', '@supabase/supabase-js': 'Supabase',
  'firebase': 'Firebase', '@firebase/app': 'Firebase',
  'bullmq': 'BullMQ', 'bull': 'Bull', 'agenda': 'Agenda',
  // JS/TS mobile / desktop
  'react-native': 'React Native', 'expo': 'Expo',
  '@ionic/react': 'Ionic', '@ionic/vue': 'Ionic', '@ionic/angular': 'Ionic',
  '@capacitor/core': 'Capacitor', 'electron': 'Electron',
  '@nativescript/core': 'NativeScript',
  // JS/TS AI
  '@anthropic-ai/sdk': 'Anthropic SDK', 'ai': 'Vercel AI SDK',
  '@langchain/core': 'LangChain', '@google/generative-ai': 'Gemini SDK',
  // JS/TS validation
  'zod': 'Zod', 'yup': 'Yup', 'joi': 'Joi', 'valibot': 'Valibot',
  // JS/TS monorepo
  'nx': 'Nx', 'turbo': 'Turborepo', 'lerna': 'Lerna',
  // Payments / BaaS
  'stripe': 'Stripe', '@stripe/stripe-js': 'Stripe',
  '@sanity/client': 'Sanity', 'sanity': 'Sanity',
}

export function techStackFromDeps(
  deps: { name: string }[]
): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const dep of deps) {
    const lower = dep.name.toLowerCase()
    const label = KNOWN_FRAMEWORKS[lower] ?? KNOWN_FRAMEWORKS[dep.name]
    if (label && !seen.has(label)) {
      seen.add(label)
      result.push(label)
    }
  }
  return result.sort()
}
