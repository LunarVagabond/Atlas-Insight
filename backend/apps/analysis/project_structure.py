import collections
import re
from datetime import datetime, timezone
from pathlib import Path

from git import Repo

STALE_BRANCH_DAYS = 90


def detect_stale_branches(repo_obj: Repo) -> tuple[list[dict], int]:
    """Return (stale_branches, stale_count) — remote branches with no commits in 90+ days."""
    now = datetime.now(tz=timezone.utc)
    stale: list[dict] = []
    try:
        for ref in repo_obj.remote().refs:
            branch_name = ref.name
            if branch_name.endswith('/HEAD'):
                continue
            try:
                commit = ref.commit
                committed_dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
                days_ago = (now - committed_dt).days
                if days_ago >= STALE_BRANCH_DAYS:
                    stale.append({
                        'name': branch_name.split('/', 1)[-1],
                        'last_commit': committed_dt.isoformat(),
                        'days_ago': days_ago,
                    })
            except Exception:
                continue
    except Exception:
        pass
    stale.sort(key=lambda b: -b['days_ago'])
    return stale, len(stale)

EXT_LANG: dict[str, str] = {
    '.py': 'Python', '.pyw': 'Python',
    '.js': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.jsx': 'JavaScript',
    '.go': 'Go',
    '.rs': 'Rust',
    '.java': 'Java',
    '.kt': 'Kotlin', '.kts': 'Kotlin',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.cs': 'C#',
    '.cpp': 'C++', '.cxx': 'C++', '.cc': 'C++',
    '.c': 'C',
    '.h': 'C/C++ Header', '.hpp': 'C++ Header',
    '.swift': 'Swift',
    '.scala': 'Scala',
    '.vue': 'Vue',
    '.svelte': 'Svelte',
    '.dart': 'Dart',
    '.r': 'R',
    '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell',
    '.html': 'HTML', '.htm': 'HTML',
    '.css': 'CSS', '.scss': 'SCSS', '.sass': 'SASS', '.less': 'Less',
    '.sql': 'SQL',
    '.tf': 'Terraform', '.hcl': 'Terraform',
    '.proto': 'Protobuf',
    '.lua': 'Lua',
    '.ex': 'Elixir', '.exs': 'Elixir',
    '.clj': 'Clojure',
    '.hs': 'Haskell',
    '.elm': 'Elm',
    '.gleam': 'Gleam',
    '.zig': 'Zig',
}

SKIP_DIRS = {
    '.git', 'node_modules', '.venv', 'venv', 'env', '__pycache__',
    '.mypy_cache', '.pytest_cache', 'dist', 'build', '.next', '.nuxt',
    'target', 'vendor', '.cargo', '.gradle', 'coverage', '.nyc_output',
    '.tox', 'htmlcov', '.eggs', '*.egg-info',
}

NON_SOURCE_LANGS = {'YAML', 'JSON', 'HTML', 'CSS', 'SCSS', 'SASS', 'Less', 'Shell', 'SQL'}

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
    'Makefile': None,  # presence alone doesn't mean CI
}

LINT_FILES = {
    '.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml', '.eslintrc.yaml',
    'ruff.toml', '.flake8', '.pylintrc', 'golangci.yml', '.golangci.yml',
    '.rubocop.yml', 'checkstyle.xml', '.scalafmt.conf', '.stylelintrc',
    'biome.json', '.prettier.config.js',
}

CONTRIBUTING_PATHS = [
    'CONTRIBUTING.md', 'CONTRIBUTING.rst', 'CONTRIBUTING.txt', 'CONTRIBUTING',
    '.github/CONTRIBUTING.md', 'docs/CONTRIBUTING.md', 'docs/contributing.md',
]

LICENSE_PATHS = [
    'LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE.rst',
    'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-Apache',
    'COPYING', 'COPYING.md', 'COPYING.txt',
    'license', 'license.md', 'license.txt',
]

COC_PATHS = [
    'CODE_OF_CONDUCT.md', '.github/CODE_OF_CONDUCT.md', 'docs/CODE_OF_CONDUCT.md',
]

SECURITY_POLICY_PATHS = [
    'SECURITY.md', '.github/SECURITY.md', 'docs/SECURITY.md',
]

CHANGELOG_PATHS = [
    'CHANGELOG.md', 'CHANGELOG.rst', 'CHANGELOG.txt', 'CHANGELOG',
    'CHANGES.md', 'CHANGES.rst', 'CHANGES', 'HISTORY.md', 'HISTORY.rst',
    'RELEASES.md', 'RELEASE_NOTES.md',
]


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

# Used by graph_analysis to filter framework imports from god modules
FRAMEWORK_PACKAGES: frozenset[str] = frozenset(FRAMEWORK_SIGNALS.keys())

_FRAMEWORK_FILE_PATTERNS: dict[str, str] = {
    # Meta-frameworks
    'nuxt.config.ts': 'Nuxt', 'nuxt.config.js': 'Nuxt',
    'next.config.ts': 'Next.js', 'next.config.js': 'Next.js', 'next.config.mjs': 'Next.js',
    'svelte.config.js': 'SvelteKit', 'svelte.config.ts': 'SvelteKit',
    'astro.config.mjs': 'Astro', 'astro.config.ts': 'Astro', 'astro.config.js': 'Astro',
    'remix.config.js': 'Remix', 'remix.config.ts': 'Remix',
    'gatsby-config.js': 'Gatsby', 'gatsby-config.ts': 'Gatsby',
    'analog.config.ts': 'Analog',
    # Frontend frameworks (config files)
    'angular.json': 'Angular',
    'vite.config.ts': 'Vite', 'vite.config.js': 'Vite', 'vite.config.mts': 'Vite',
    'webpack.config.js': 'Webpack', 'webpack.config.ts': 'Webpack',
    'tailwind.config.js': 'Tailwind', 'tailwind.config.ts': 'Tailwind',
    'tailwind.config.cjs': 'Tailwind',
    'ember-cli-build.js': 'Ember', 'app/router.js': 'Ember',
    # Desktop
    'src-tauri/tauri.conf.json': 'Tauri', 'tauri.conf.json': 'Tauri',
    'src-tauri/Cargo.toml': 'Tauri',
    'electron-builder.yml': 'Electron', 'electron-builder.json': 'Electron',
    'forge.config.js': 'Electron', 'forge.config.ts': 'Electron',
    # Mobile
    'app.json': 'Expo',  # Expo projects always have app.json with expo key
    'capacitor.config.ts': 'Capacitor', 'capacitor.config.json': 'Capacitor',
    # Backend config files
    'manage.py': 'Django',
    'config/routes.rb': 'Rails', 'config/application.rb': 'Rails',
    'mix.exs': 'Elixir',
    'pubspec.yaml': 'Flutter',
    'composer.json': None,  # needs content check — handled in _detect_tech_stack
    # Monorepo
    'nx.json': 'Nx', 'turbo.json': 'Turborepo', 'lerna.json': 'Lerna',
    # Infrastructure / tooling worth noting
    'Dockerfile': None,  # presence doesn't tell us the framework
    'docker-compose.yml': None,
}


def _detect_tech_stack(repo_dir: str, dep_list: list[dict]) -> list[str]:
    detected: set[str] = set()
    base = Path(repo_dir)

    # From dependencies
    for dep in dep_list:
        name = dep.get('name', '').lower()
        if name in FRAMEWORK_SIGNALS:
            detected.add(FRAMEWORK_SIGNALS[name])
        else:
            # Partial match for scoped packages and module paths
            for key, label in FRAMEWORK_SIGNALS.items():
                if name == key or name.endswith('/' + key) or name.startswith(key + '/'):
                    detected.add(label)
                    break

    # From config files
    for filename, label in _FRAMEWORK_FILE_PATTERNS.items():
        if (base / filename).exists():
            detected.add(label)

    return sorted(detected)


def analyze_structure(repo_obj: Repo, repo_dir: str, deps: dict | None = None) -> dict:
    base = Path(repo_dir)

    # Language breakdown and file stats
    lang_files: dict[str, int] = collections.defaultdict(int)
    lang_lines: dict[str, int] = collections.defaultdict(int)
    total_files = 0
    test_files = 0
    file_count_limit = 25000

    all_file_paths: list[str] = []
    for path in _walk_files(base, file_count_limit):
        total_files += 1
        if len(all_file_paths) < 5000:
            all_file_paths.append(str(path.relative_to(base)))
        ext = path.suffix.lower()
        lang = EXT_LANG.get(ext)
        is_test = _is_test_file(path, base)
        if is_test:
            test_files += 1
        if lang:
            lang_files[lang] += 1
            if path.stat().st_size < 512_000:
                try:
                    lines = path.read_text(errors='ignore').count('\n')
                    lang_lines[lang] += lines
                except Exception:
                    pass

    total_lines = sum(lang_lines.values())
    languages = sorted(
        [
            {
                'name': lang,
                'files': lang_files[lang],
                'lines': lang_lines.get(lang, 0),
                'pct': round(lang_lines.get(lang, 0) / max(total_lines, 1) * 100, 1),
            }
            for lang in lang_files
        ],
        key=lambda x: -x['lines'],
    )[:15]

    # CI systems
    ci_systems = [
        name
        for path_str, name in CI_PATHS.items()
        if name and (base / path_str).exists()
    ]
    gh_wf_dir = base / '.github' / 'workflows'
    gh_workflow_count = (
        len(list(gh_wf_dir.glob('*.yml')) + list(gh_wf_dir.glob('*.yaml')))
        if gh_wf_dir.is_dir()
        else 0
    )

    # Lint config
    has_lint = any((base / f).exists() for f in LINT_FILES)
    if not has_lint:
        ppt = base / 'pyproject.toml'
        if ppt.exists():
            try:
                c = ppt.read_text(errors='ignore')
                has_lint = any(
                    tag in c for tag in ('[tool.ruff]', '[tool.flake8]', '[tool.pylint]')
                )
            except Exception:
                pass

    # Docker
    has_docker = any(
        (base / f).exists()
        for f in ('Dockerfile', 'docker-compose.yml', 'docker-compose.yaml')
    )

    # Community health files
    has_contributing = _find_file(base, CONTRIBUTING_PATHS)
    license_file = _find_file(base, LICENSE_PATHS)
    coc_file = _find_file(base, COC_PATHS)
    security_policy_file = _find_file(base, SECURITY_POLICY_PATHS)
    changelog_file = _find_file(base, CHANGELOG_PATHS)
    roadmap_file = _find_file(base, [
        'ROADMAP.md', 'ROADMAP.rst', 'ROADMAP.txt', 'ROADMAP',
        'roadmap.md', 'roadmap.rst', 'TODO.md', 'todo.md',
        'docs/ROADMAP.md', 'docs/roadmap.md',
    ])

    # License detection from file content
    license_type = None
    if license_file:
        license_type = _detect_license_type(base / license_file)

    # Read community file content (truncated to 12KB each)
    community_files_content = _read_community_files(
        base,
        contributing=has_contributing,
        license_f=license_file,
        coc=coc_file,
        security=security_policy_file,
        changelog=changelog_file,
    )

    # Releases / tags
    release_count, releases = _get_releases(repo_obj)

    # Repo age from first commit
    repo_age_days = _get_repo_age(repo_obj)

    # Bus factor
    bus_factor, top_contributors = _compute_bus_factor(repo_obj)

    # Hot files (most-changed in last 300 commits)
    hot_files = _get_hot_files(repo_obj)

    # Tech stack detection from dependencies + config files
    dep_list = deps.get('dependencies', []) if deps else []
    tech_stack = _detect_tech_stack(repo_dir, dep_list)

    source_files = sum(
        v for lang, v in lang_files.items() if lang not in NON_SOURCE_LANGS
    )
    test_ratio = round(test_files / max(source_files, 1), 3)

    stale_branches, stale_branch_count = detect_stale_branches(repo_obj)

    return {
        'total_files': total_files,
        'total_lines': total_lines,
        'languages': languages,
        'test_files': test_files,
        'test_ratio': test_ratio,
        'has_ci': bool(ci_systems),
        'ci_systems': ci_systems,
        'gh_workflow_count': gh_workflow_count,
        'has_docker': has_docker,
        'has_lint_config': has_lint,
        'has_contributing': bool(has_contributing),
        'contributing_file': has_contributing,
        'license_file': license_file,
        'license_type': license_type,
        'has_coc': bool(coc_file),
        'coc_file': coc_file,
        'has_security_policy': bool(security_policy_file),
        'security_policy_file': security_policy_file,
        'has_changelog': bool(changelog_file),
        'changelog_file': changelog_file,
        'roadmap_file': roadmap_file,
        'roadmap_parsed': _parse_roadmap_file(base, roadmap_file),
        'community_files_content': community_files_content,
        'releases': releases,
        'release_count': release_count,
        'last_release': releases[0] if releases else None,
        'repo_age_days': repo_age_days,
        'bus_factor': bus_factor,
        'top_contributors': top_contributors,
        'hot_files': hot_files,
        'tech_stack': tech_stack,
        'all_files': all_file_paths,
        'stale_branches': stale_branches,
        'stale_branch_count': stale_branch_count,
    }


def _walk_files(base: Path, max_files: int = 25000):
    count = 0
    for path in base.rglob('*'):
        if count >= max_files:
            break
        if path.is_file():
            rel = path.relative_to(base)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            count += 1
            yield path


def _is_test_file(path: Path, base: Path) -> bool:
    rel = path.relative_to(base)
    name = path.stem.lower()
    parts_lower = [p.lower() for p in rel.parts]
    if any(p in ('test', 'tests', '__tests__', 'spec', 'specs', 'e2e') for p in parts_lower):
        return True
    return (
        name.startswith('test_')
        or name.endswith('_test')
        or name.endswith('.test')
        or name.endswith('.spec')
        or name.endswith('_spec')
        or name.startswith('spec_')
    )


def _parse_roadmap_file(base: Path, roadmap_file: str | None) -> dict | None:
    if not roadmap_file:
        return None
    try:
        from .roadmap_parser import parse_roadmap
        content = (base / roadmap_file).read_text(errors='ignore')
        return parse_roadmap(content)
    except Exception:
        return None


def _find_file(base: Path, candidates: list[str]) -> str | None:
    for name in candidates:
        if (base / name).exists():
            return name
    return None


def _detect_license_type(path: Path) -> str | None:
    try:
        content = path.read_text(errors='ignore').lower()[:2000]
    except Exception:
        return None
    if 'mit license' in content or 'permission is hereby granted' in content:
        return 'MIT'
    if 'apache license' in content and '2.0' in content:
        return 'Apache-2.0'
    if 'gnu general public license' in content:
        if 'version 3' in content:
            return 'GPL-3.0'
        if 'version 2' in content:
            return 'GPL-2.0'
        return 'GPL'
    if 'gnu lesser general public license' in content:
        return 'LGPL'
    if 'mozilla public license' in content:
        return 'MPL-2.0'
    if 'bsd 2-clause' in content or 'redistribution and use in source' in content:
        if 'neither the name' not in content:
            return 'BSD-2-Clause'
        return 'BSD-3-Clause'
    if 'the unlicense' in content or 'this is free and unencumbered software' in content:
        return 'Unlicense'
    if 'isc license' in content:
        return 'ISC'
    return 'Other'


def _get_releases(repo_obj: Repo) -> tuple[int, list[dict]]:
    try:
        tags = sorted(repo_obj.tags, key=lambda t: t.commit.committed_date, reverse=True)
        recent = [
            {
                'name': t.name,
                'date': datetime.fromtimestamp(
                    t.commit.committed_date, tz=timezone.utc
                ).isoformat(),
            }
            for t in tags[:20]
        ]
        return len(tags), recent
    except Exception:
        return 0, []


def _get_repo_age(repo_obj: Repo) -> int | None:
    try:
        count_str = repo_obj.git.rev_list('HEAD', '--count', '--first-parent')
        total = int(count_str.strip())
        skip = max(0, total - 1)
        ts_str = repo_obj.git.log(f'--skip={skip}', '-1', '--format=%ct', 'HEAD', '--first-parent')
        if ts_str.strip():
            first_date = datetime.fromtimestamp(int(ts_str.strip()), tz=timezone.utc)
            return (datetime.now(timezone.utc) - first_date).days
    except Exception:
        pass
    return None


def _compute_bus_factor(repo_obj: Repo) -> tuple[int, list[dict]]:
    author_files: dict[str, set] = collections.defaultdict(set)
    email_to_name: dict[str, str] = {}
    try:
        # AUTHOR: prefix lets us skip blank lines safely.
        # Without it, git inserts a blank line between the email and the
        # --name-only file list, which resets current_author so the first
        # filename after each commit is misidentified as the next author.
        # Format: AUTHOR:<email>|<name> so we capture display name too.
        output = repo_obj.git.log('--format=AUTHOR:%ae|%an', '--name-only', '-300', 'HEAD')
        current_author: str | None = None
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('AUTHOR:'):
                parts = line[7:].split('|', 1)
                current_author = parts[0]
                if current_author and len(parts) > 1 and parts[1]:
                    email_to_name[current_author] = parts[1]
            elif current_author:
                author_files[current_author].add(line)
    except Exception:
        return 1, []

    if not author_files:
        return 1, []

    all_files: set[str] = set()
    for files in author_files.values():
        all_files.update(files)

    sorted_authors = sorted(author_files.items(), key=lambda x: -len(x[1]))
    top_contributors = [
        {
            'author': email_to_name.get(a, a),
            'email': a,
            'files_touched': len(f),
        }
        for a, f in sorted_authors[:10]
    ]

    total_authors = len(author_files)
    target = len(all_files) * 0.8
    covered: set[str] = set()
    bus_factor = 0
    for author, files in sorted_authors:
        covered.update(files)
        bus_factor += 1
        if len(covered) >= target:
            break

    # Bus factor can never exceed the actual number of unique contributors
    return min(max(1, bus_factor), total_authors), top_contributors


def _get_hot_files(repo_obj: Repo) -> list[dict]:
    file_counts: dict[str, int] = collections.Counter()
    try:
        output = repo_obj.git.log('--format=', '--name-only', '-300', 'HEAD')
        for line in output.splitlines():
            line = line.strip()
            if line:
                file_counts[line] += 1
    except Exception:
        return []
    return [{'file': f, 'commit_count': c} for f, c in file_counts.most_common(20)]


def _read_community_files(
    base: Path,
    contributing: str | None,
    license_f: str | None,
    coc: str | None,
    security: str | None,
    changelog: str | None,
    max_bytes: int = 12_000,
) -> dict:
    result: dict[str, str | None] = {}
    mapping = {
        'contributing': contributing,
        'license': license_f,
        'coc': coc,
        'security': security,
        'changelog': changelog,
    }
    for key, filename in mapping.items():
        if not filename:
            result[key] = None
            continue
        try:
            content = (base / filename).read_text(errors='replace')
            if len(content) > max_bytes:
                content = content[:max_bytes] + '\n\n[… truncated …]'
            result[key] = content
        except Exception:
            result[key] = None
    return result


def _parse_license_spdx_from_content(content: str) -> str | None:
    """Detect SPDX identifier from license file content."""
    spdx_map = {
        'MIT': r'mit license|permission is hereby granted',
        'Apache-2.0': r'apache license.*2\.0',
        'GPL-3.0': r'gnu general public license.*version 3',
        'GPL-2.0': r'gnu general public license.*version 2',
        'BSD-3-Clause': r'neither the name.*nor the names',
        'BSD-2-Clause': r'redistribution and use in source.*neither',
        'ISC': r'isc license',
        'MPL-2.0': r'mozilla public license.*2\.0',
        'LGPL-2.1': r'gnu lesser general public license.*2\.1',
        'LGPL-3.0': r'gnu lesser general public license.*3',
        'Unlicense': r'this is free and unencumbered',
        'CC0-1.0': r'creative commons.*cc0',
    }
    lower = content.lower()
    for spdx, pattern in spdx_map.items():
        if re.search(pattern, lower):
            return spdx
    return None
