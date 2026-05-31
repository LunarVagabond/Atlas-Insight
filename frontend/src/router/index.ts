import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

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
      path: '/spotlight',
      name: 'spotlight',
      component: () => import('../views/SpotlightView.vue'),
    },
  ],
})

export default router
