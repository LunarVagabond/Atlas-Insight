from pathlib import Path

FRAMEWORK_SIGNALS: dict[str, str] = {
    # ── Python web ────────────────────────────────────────────────────────────
    'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
    'starlette': 'Starlette', 'tornado': 'Tornado', 'bottle': 'Bottle',
    'sanic': 'Sanic', 'litestar': 'Litestar', 'falcon': 'Falcon',
    'aiohttp': 'aiohttp', 'robyn': 'Robyn', 'blacksheep': 'BlackSheep',
    'quart': 'Quart', 'masonite': 'Masonite',
    # Python ORMs / DB
    'sqlalchemy': 'SQLAlchemy', 'tortoise-orm': 'Tortoise ORM',
    'peewee': 'Peewee', 'pony': 'Pony ORM', 'mongoengine': 'MongoEngine',
    'motor': 'Motor', 'alembic': 'Alembic', 'databases': 'Databases',
    # Python task queues
    'celery': 'Celery', 'rq': 'RQ', 'dramatiq': 'Dramatiq',
    'huey': 'Huey', 'arq': 'Arq', 'apscheduler': 'APScheduler',
    # Python API / auth
    'djangorestframework': 'DRF', 'django-ninja': 'Django Ninja',
    'graphene': 'Graphene', 'strawberry-graphql': 'Strawberry',
    'django-allauth': 'django-allauth', 'authlib': 'Authlib',
    # Python testing
    'pytest': 'pytest', 'hypothesis': 'Hypothesis', 'factory-boy': 'factory_boy',
    'locust': 'Locust',
    # Python data / ML / AI
    'numpy': 'NumPy', 'pandas': 'Pandas', 'scikit-learn': 'scikit-learn',
    'torch': 'PyTorch', 'pytorch': 'PyTorch', 'tensorflow': 'TensorFlow',
    'keras': 'Keras', 'transformers': 'Hugging Face', 'diffusers': 'Diffusers',
    'langchain': 'LangChain', 'llama-index': 'LlamaIndex', 'llama_index': 'LlamaIndex',
    'openai': 'OpenAI SDK', 'anthropic': 'Anthropic SDK',
    'streamlit': 'Streamlit', 'gradio': 'Gradio', 'dash': 'Dash',
    'dask': 'Dask', 'ray': 'Ray', 'polars': 'Polars',
    'fastai': 'fastai', 'xgboost': 'XGBoost', 'lightgbm': 'LightGBM',
    'scipy': 'SciPy', 'matplotlib': 'Matplotlib', 'plotly': 'Plotly',
    # Python async / messaging
    'pika': 'RabbitMQ', 'aiokafka': 'Kafka', 'kafka-python': 'Kafka',
    'redis': 'Redis', 'aioredis': 'Redis', 'pymongo': 'MongoDB',
    'asyncpg': 'asyncpg', 'psycopg2': 'psycopg2', 'psycopg': 'psycopg3',
    # ── Ruby ──────────────────────────────────────────────────────────────────
    'rails': 'Rails', 'sinatra': 'Sinatra', 'hanami': 'Hanami',
    'grape': 'Grape', 'padrino': 'Padrino', 'roda': 'Roda',
    'sidekiq': 'Sidekiq', 'devise': 'Devise', 'pundit': 'Pundit',
    'rspec-rails': 'RSpec', 'capybara': 'Capybara',
    # ── Go ────────────────────────────────────────────────────────────────────
    'gin-gonic/gin': 'Gin', 'labstack/echo': 'Echo', 'gofiber/fiber': 'Fiber',
    'gorilla/mux': 'Gorilla Mux', 'go-chi/chi': 'Chi', 'chi': 'Chi',
    'beego/beego': 'Beego', 'gobuffalo/buffalo': 'Buffalo',
    'go-iris/iris': 'Iris', 'urfave/negroni': 'Negroni',
    'go-kit/kit': 'Go kit', 'gorm.io/gorm': 'GORM', 'ent/ent': 'Ent',
    'stretchr/testify': 'Testify', 'uber-go/zap': 'Zap',
    'grpc-ecosystem/grpc-gateway': 'gRPC-Gateway',
    'google/wire': 'Wire', 'uber-go/fx': 'Fx',
    # ── Rust ──────────────────────────────────────────────────────────────────
    'actix-web': 'Actix', 'rocket': 'Rocket', 'axum': 'Axum', 'warp': 'Warp',
    'poem': 'Poem', 'salvo': 'Salvo', 'tide': 'Tide', 'ntex': 'ntex',
    'tauri': 'Tauri', '@tauri-apps/api': 'Tauri', '@tauri-apps/plugin-shell': 'Tauri',
    'diesel': 'Diesel', 'sea-orm': 'SeaORM', 'sqlx': 'SQLx',
    'tokio': 'Tokio', 'serde': 'Serde', 'tonic': 'Tonic',
    'bevy': 'Bevy', 'leptos': 'Leptos', 'yew': 'Yew', 'dioxus': 'Dioxus',
    # ── Java / Kotlin / JVM ───────────────────────────────────────────────────
    'spring-boot': 'Spring Boot', 'spring': 'Spring',
    'ktor': 'Ktor', 'micronaut': 'Micronaut', 'quarkus': 'Quarkus',
    'dropwizard': 'Dropwizard', 'javalin': 'Javalin', 'helidon': 'Helidon',
    'vertx': 'Vert.x', 'http4k': 'http4k',
    'hibernate': 'Hibernate', 'exposed': 'Exposed', 'jooq': 'jOOQ',
    'junit': 'JUnit', 'mockito': 'Mockito',
    # ── PHP ───────────────────────────────────────────────────────────────────
    'laravel/framework': 'Laravel', 'symfony/symfony': 'Symfony',
    'slim/slim': 'Slim', 'cakephp/cakephp': 'CakePHP',
    'yiisoft/yii2': 'Yii2', 'codeigniter4/framework': 'CodeIgniter',
    'phalcon/cphalcon': 'Phalcon', 'laminas/laminas-mvc': 'Laminas',
    'laravel/lumen-framework': 'Lumen', 'spiral/framework': 'Spiral',
    # ── C# / .NET ─────────────────────────────────────────────────────────────
    'microsoft.aspnetcore': 'ASP.NET Core', 'aspnetcore': 'ASP.NET Core',
    'nancy': 'Nancy', 'servicestack': 'ServiceStack',
    'mediatr': 'MediatR', 'dapper': 'Dapper',
    'microsoft.entityframeworkcore': 'Entity Framework',
    'xunit': 'xUnit', 'nunit': 'NUnit',
    # ── Elixir ────────────────────────────────────────────────────────────────
    'phoenix': 'Phoenix', 'ecto': 'Ecto', 'absinthe': 'Absinthe',
    'plug': 'Plug', 'oban': 'Oban', 'broadway': 'Broadway',
    # ── Haskell ───────────────────────────────────────────────────────────────
    'servant': 'Servant', 'yesod': 'Yesod', 'scotty': 'Scotty',
    'wai': 'WAI', 'persistent': 'Persistent',
    # ── Scala ─────────────────────────────────────────────────────────────────
    'play': 'Play Framework', 'akka-http': 'Akka HTTP',
    'zio-http': 'ZIO HTTP', 'http4s': 'http4s', 'tapir': 'Tapir',
    # ── Dart / Flutter ────────────────────────────────────────────────────────
    'flutter': 'Flutter', 'shelf': 'Shelf', 'serverpod': 'Serverpod',
    'flutter_bloc': 'flutter_bloc', 'riverpod': 'Riverpod',
    'provider': 'Provider', 'get': 'GetX', 'dio': 'Dio',
    'get_it': 'get_it', 'go_router': 'go_router',
    # ── JS/TS frontend ────────────────────────────────────────────────────────
    'vue': 'Vue', 'react': 'React', 'svelte': 'Svelte',
    'solid-js': 'Solid', 'astro': 'Astro', '@angular/core': 'Angular',
    'preact': 'Preact', 'lit': 'Lit', 'alpinejs': 'Alpine.js',
    '@alpinejs/core': 'Alpine.js', '@hotwired/stimulus': 'Stimulus',
    'stimulus': 'Stimulus', 'jquery': 'jQuery', 'htmx.org': 'HTMX',
    'htmx': 'HTMX', '@builder.io/qwik': 'Qwik', 'qwik': 'Qwik',
    'marko': 'Marko', 'mithril': 'Mithril', 'inferno': 'Inferno',
    'hyperapp': 'Hyperapp', 'stencil': 'Stencil',
    # JS/TS meta-frameworks
    'next': 'Next.js', 'nuxt': 'Nuxt', '@nuxt/core': 'Nuxt',
    'remix': 'Remix', '@sveltejs/kit': 'SvelteKit',
    'gatsby': 'Gatsby', '@shopify/hydrogen': 'Hydrogen',
    '@tanstack/start': 'TanStack Start', 'analog': 'Analog',
    # JS/TS backend
    'express': 'Express', 'fastify': 'Fastify', 'koa': 'Koa',
    'hono': 'Hono', '@nestjs/core': 'NestJS', 'nestjs': 'NestJS',
    '@adonisjs/core': 'AdonisJS', 'adonis': 'AdonisJS',
    '@feathersjs/feathers': 'Feathers', 'sails': 'Sails',
    'polka': 'Polka', 'h3': 'H3', 'elysia': 'Elysia',
    'hapi': 'Hapi', '@hapi/hapi': 'Hapi', 'restify': 'Restify',
    'loopback': 'LoopBack', '@loopback/core': 'LoopBack',
    'strapi': 'Strapi', '@strapi/strapi': 'Strapi',
    'directus': 'Directus', 'payload': 'Payload CMS',
    # JS/TS ORMs / DB
    'prisma': 'Prisma', 'typeorm': 'TypeORM', 'sequelize': 'Sequelize',
    'mongoose': 'Mongoose', 'drizzle-orm': 'Drizzle',
    'mikro-orm': 'MikroORM', '@mikro-orm/core': 'MikroORM',
    'objection': 'Objection', 'bookshelf': 'Bookshelf', 'knex': 'Knex',
    '@databases/pg': 'Databases', 'pg': 'node-postgres',
    # JS/TS GraphQL / API
    'graphql': 'GraphQL', '@trpc/server': 'tRPC', 'trpc': 'tRPC',
    '@grpc/grpc-js': 'gRPC', 'grpc': 'gRPC',
    '@apollo/server': 'Apollo Server', 'apollo-server': 'Apollo Server',
    '@apollo/client': 'Apollo Client', 'urql': 'URQL',
    'pothos-graphql': 'Pothos',
    # JS/TS state management
    'pinia': 'Pinia', 'redux': 'Redux', '@reduxjs/toolkit': 'Redux Toolkit',
    'zustand': 'Zustand', 'jotai': 'Jotai', 'recoil': 'Recoil',
    'mobx': 'MobX', 'valtio': 'Valtio', 'xstate': 'XState',
    '@xstate/react': 'XState', 'nanostores': 'Nanostores',
    'effector': 'Effector', '@legendapp/state': 'Legend State',
    'rxjs': 'RxJS', 'ngrx': '@ngrx',
    # JS/TS UI / component libraries
    'tailwindcss': 'Tailwind', 'daisyui': 'DaisyUI', 'bootstrap': 'Bootstrap',
    'bulma': 'Bulma', 'foundation-sites': 'Foundation',
    '@mui/material': 'MUI', '@mui/joy': 'MUI Joy',
    'antd': 'Ant Design', '@ant-design/react': 'Ant Design',
    'chakra-ui': 'Chakra UI', '@chakra-ui/react': 'Chakra UI',
    '@mantine/core': 'Mantine', '@headlessui/react': 'Headless UI',
    '@headlessui/vue': 'Headless UI', '@radix-ui/react-primitive': 'Radix UI',
    'vuetify': 'Vuetify', 'primevue': 'PrimeVue',
    'element-plus': 'Element Plus', 'naive-ui': 'Naive UI',
    'quasar': 'Quasar', '@quasar/app': 'Quasar', 'vant': 'Vant',
    'styled-components': 'Styled Components',
    '@emotion/react': 'Emotion', '@emotion/styled': 'Emotion',
    '@vanilla-extract/css': 'vanilla-extract', 'stitches': 'Stitches',
    '@angular/material': 'Angular Material', 'primeng': 'PrimeNG',
    'shadcn-ui': 'shadcn/ui',
    # JS/TS testing
    'jest': 'Jest', 'vitest': 'Vitest', 'mocha': 'Mocha',
    'jasmine': 'Jasmine', 'ava': 'Ava', '@playwright/test': 'Playwright',
    'playwright': 'Playwright', 'cypress': 'Cypress',
    'puppeteer': 'Puppeteer', '@testing-library/react': 'Testing Library',
    '@testing-library/vue': 'Testing Library', '@testing-library/dom': 'Testing Library',
    'supertest': 'Supertest', 'chai': 'Chai', 'sinon': 'Sinon',
    'storybook': 'Storybook', '@storybook/react': 'Storybook',
    'k6': 'k6',
    # JS/TS build / bundlers
    'vite': 'Vite', 'webpack': 'Webpack', 'turbopack': 'Turbopack',
    'parcel': 'Parcel', 'esbuild': 'esbuild', 'rollup': 'Rollup',
    '@rspack/core': 'Rspack', 'tsup': 'tsup', '@biomejs/biome': 'Biome',
    # JS/TS data fetching / query
    '@tanstack/react-query': 'TanStack Query', '@tanstack/vue-query': 'TanStack Query',
    'swr': 'SWR', 'rtk-query': 'RTK Query',
    # JS/TS auth
    'passport': 'Passport', 'next-auth': 'NextAuth', '@auth/core': 'Auth.js',
    '@clerk/nextjs': 'Clerk', '@clerk/clerk-react': 'Clerk', 'lucia': 'Lucia',
    # JS/TS realtime / messaging
    'socket.io': 'Socket.io', 'ws': 'ws', 'ably': 'Ably',
    '@supabase/supabase-js': 'Supabase', 'firebase': 'Firebase',
    '@firebase/app': 'Firebase', '@firebase/firestore': 'Firestore',
    'bullmq': 'BullMQ', 'bull': 'Bull', 'agenda': 'Agenda',
    # JS/TS mobile / desktop
    'react-native': 'React Native', 'expo': 'Expo',
    '@ionic/react': 'Ionic', '@ionic/vue': 'Ionic', '@ionic/angular': 'Ionic',
    '@capacitor/core': 'Capacitor', 'electron': 'Electron',
    '@nativescript/core': 'NativeScript',
    # JS/TS AI / ML
    'openai': 'OpenAI SDK', '@anthropic-ai/sdk': 'Anthropic SDK',
    '@langchain/core': 'LangChain', 'ai': 'Vercel AI SDK',
    '@google/generative-ai': 'Gemini SDK',
    # JS/TS validation
    'zod': 'Zod', 'yup': 'Yup', 'joi': 'Joi', 'valibot': 'Valibot',
    'class-validator': 'class-validator',
    # JS/TS monorepo / tooling
    'nx': 'Nx', 'turbo': 'Turborepo', 'lerna': 'Lerna',
    'changesets': 'Changesets',
    # JS/TS HTTP clients
    'axios': 'Axios', 'got': 'Got', 'ky': 'Ky',
    # Payments / CMS / infra
    'stripe': 'Stripe', '@stripe/stripe-js': 'Stripe',
    'contentful': 'Contentful', 'sanity': 'Sanity',
    '@sanity/client': 'Sanity', 'ghost': 'Ghost',
}

FRAMEWORK_PACKAGES: frozenset[str] = frozenset(FRAMEWORK_SIGNALS.keys())

CI_PATHS: dict[str, str] = {
    '.github/workflows': 'GitHub Actions',
    '.travis.yml': 'Travis CI',
    '.circleci': 'CircleCI',
    'Jenkinsfile': 'Jenkins',
    '.gitlab-ci.yml': 'GitLab CI',
    'bitbucket-pipelines.yml': 'Bitbucket Pipelines',
    'azure-pipelines.yml': 'Azure Pipelines',
    '.drone.yml': 'Drone CI',
    'circle.yml': 'CircleCI',
    '.buildkite': 'Buildkite',
    'Makefile': None,
}

LINT_FILES = {
    '.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml', '.eslintrc.yaml',
    'eslint.config.js', 'eslint.config.mjs', 'eslint.config.ts', 'eslint.config.cjs',
    'ruff.toml', '.flake8', '.pylintrc', 'golangci.yml', '.golangci.yml',
    '.rubocop.yml', 'checkstyle.xml', '.scalafmt.conf', '.stylelintrc',
    'biome.json', '.prettier.config.js',
}

_FRAMEWORK_FILE_PATTERNS: dict[str, str] = {
    'nuxt.config.ts': 'Nuxt', 'nuxt.config.js': 'Nuxt',
    'next.config.ts': 'Next.js', 'next.config.js': 'Next.js', 'next.config.mjs': 'Next.js',
    'svelte.config.js': 'SvelteKit', 'svelte.config.ts': 'SvelteKit',
    'astro.config.mjs': 'Astro', 'astro.config.ts': 'Astro', 'astro.config.js': 'Astro',
    'remix.config.js': 'Remix', 'remix.config.ts': 'Remix',
    'gatsby-config.js': 'Gatsby', 'gatsby-config.ts': 'Gatsby',
    'analog.config.ts': 'Analog',
    'angular.json': 'Angular',
    'vite.config.ts': 'Vite', 'vite.config.js': 'Vite', 'vite.config.mts': 'Vite',
    'webpack.config.js': 'Webpack', 'webpack.config.ts': 'Webpack',
    'tailwind.config.js': 'Tailwind', 'tailwind.config.ts': 'Tailwind',
    'tailwind.config.cjs': 'Tailwind',
    'ember-cli-build.js': 'Ember', 'app/router.js': 'Ember',
    'src-tauri/tauri.conf.json': 'Tauri', 'tauri.conf.json': 'Tauri',
    'src-tauri/Cargo.toml': 'Tauri',
    'electron-builder.yml': 'Electron', 'electron-builder.json': 'Electron',
    'forge.config.js': 'Electron', 'forge.config.ts': 'Electron',
    'app.json': 'Expo',
    'capacitor.config.ts': 'Capacitor', 'capacitor.config.json': 'Capacitor',
    'manage.py': 'Django',
    'config/routes.rb': 'Rails', 'config/application.rb': 'Rails',
    'mix.exs': 'Elixir',
    'pubspec.yaml': 'Flutter',
    'composer.json': None,
    'nx.json': 'Nx', 'turbo.json': 'Turborepo', 'lerna.json': 'Lerna',
    'Dockerfile': None,
    'docker-compose.yml': None,
}


def detect_tech_stack(repo_dir: str, dep_list: list[dict]) -> list[str]:
    detected: set[str] = set()
    base = Path(repo_dir)

    for dep in dep_list:
        name = dep.get('name', '').lower()
        if name in FRAMEWORK_SIGNALS:
            detected.add(FRAMEWORK_SIGNALS[name])
        else:
            for key, label in FRAMEWORK_SIGNALS.items():
                if name == key or name.endswith('/' + key) or name.startswith(key + '/'):
                    detected.add(label)
                    break

    for filename, label in _FRAMEWORK_FILE_PATTERNS.items():
        if label is not None and (base / filename).exists():
            detected.add(label)

    return sorted(detected)
