export const KNOWN_FRAMEWORKS: Record<string, string> = {
  'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
  'celery': 'Celery', 'sqlalchemy': 'SQLAlchemy', 'tortoise-orm': 'Tortoise ORM',
  'starlette': 'Starlette',
  'rails': 'Rails', 'sinatra': 'Sinatra',
  'gin-gonic/gin': 'Gin', 'labstack/echo': 'Echo', 'gofiber/fiber': 'Fiber',
  'gorilla/mux': 'Gorilla Mux',
  'actix-web': 'Actix', 'rocket': 'Rocket', 'axum': 'Axum', 'warp': 'Warp',
  'spring-boot': 'Spring Boot', 'spring': 'Spring', 'ktor': 'Ktor',
  'vue': 'Vue', 'react': 'React', 'svelte': 'Svelte',
  'solid-js': 'Solid', 'astro': 'Astro',
  '@angular/core': 'Angular', 'preact': 'Preact', 'lit': 'Lit',
  'next': 'Next.js', 'nuxt': 'Nuxt', 'remix': 'Remix',
  '@sveltejs/kit': 'SvelteKit', 'gatsby': 'Gatsby',
  'express': 'Express', 'fastify': 'Fastify', 'koa': 'Koa',
  'hono': 'Hono', '@nestjs/core': 'NestJS', 'nestjs': 'NestJS',
  'prisma': 'Prisma', 'typeorm': 'TypeORM', 'sequelize': 'Sequelize',
  'mongoose': 'Mongoose', 'drizzle-orm': 'Drizzle',
  'graphql': 'GraphQL', '@trpc/server': 'tRPC', 'trpc': 'tRPC',
  'pytest': 'pytest', 'jest': 'Jest', 'vitest': 'Vitest', 'cypress': 'Cypress',
  'vite': 'Vite', 'webpack': 'Webpack',
  'pinia': 'Pinia', 'redux': 'Redux', 'zustand': 'Zustand',
  'tailwindcss': 'Tailwind', '@mui/material': 'MUI',
  'antd': 'Ant Design',
}

export function techStackFromDeps(
  deps: { name: string }[]
): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const dep of deps) {
    const label = KNOWN_FRAMEWORKS[dep.name]
    if (label && !seen.has(label)) {
      seen.add(label)
      result.push(label)
    }
  }
  return result.sort()
}
