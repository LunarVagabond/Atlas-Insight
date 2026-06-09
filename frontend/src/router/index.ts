import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { useFeatureFlagsStore } from '../stores/featureFlags'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/results/:runId',
      name: 'results',
      component: () => import('../views/ResultsView.vue'),
    },
    {
      path: '/print/:runId',
      name: 'print',
      component: () => import('../views/PrintView.vue'),
    },
    {
      path: '/runs',
      name: 'runs',
      component: () => import('../views/RunsView.vue'),
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('../views/CompareView.vue'),
    },
    {
      path: '/r/:owner/:name',
      name: 'repo-permalink',
      component: () => import('../views/RepoView.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: '/learn',
      name: 'learn',
      component: () => import('../views/LearnView.vue'),
    },
    {
      path: '/resources',
      name: 'resources',
      component: () => import('../views/ResourcesView.vue'),
    },
    {
      path: '/supported',
      name: 'supported',
      component: () => import('../views/SupportedView.vue'),
    },
    {
      path: '/spotlight',
      name: 'spotlight',
      component: () => import('../views/SpotlightView.vue'),
    },
    {
      path: '/trending',
      name: 'trending',
      component: () => import('../views/TrendingView.vue'),
    },
    {
      path: '/docs/:slug',
      name: 'docs',
      component: () => import('../views/DocsPageView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const flags = useFeatureFlagsStore()
  if (!flags.loaded) await flags.fetchFlags()
  if (to.name === 'spotlight' && !flags.spotlight) return { name: 'home' }
  if (to.name === 'trending' && !flags.trending) return { name: 'home' }
})

export default router
