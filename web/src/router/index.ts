import { createRouter, createWebHistory } from 'vue-router'
import { CAP_ACCOUNT_MANAGE, CAP_CONTROL_PANEL } from '@/constants/access'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, titleKey: 'login.submit' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false, titleKey: 'register.submit' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true, requiredCapability: CAP_CONTROL_PANEL },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { titleKey: 'dashboard.title' } },
      { path: 'core', name: 'core', component: () => import('@/views/CoreView.vue'), meta: { titleKey: 'core.title' } },
      { path: 'plugins', name: 'plugins', component: () => import('@/views/PluginsView.vue'), meta: { titleKey: 'plugins.title' } },
      { path: 'permissions', name: 'permissions', component: () => import('@/views/PermissionsView.vue'), meta: { titleKey: 'permissions.title' } },
      { path: 'groups', name: 'groups', component: () => import('@/views/GroupsView.vue'), meta: { titleKey: 'groups.title' } },
      { path: 'logs', name: 'logs', component: () => import('@/views/LogsView.vue'), meta: { titleKey: 'logs.liveTitle' } },
      { path: 'logs/history', name: 'logs-history', component: () => import('@/views/LogHistoryView.vue'), meta: { titleKey: 'logs.historyTitle' } },
      { path: 'data', name: 'data', component: () => import('@/views/DataView.vue'), meta: { titleKey: 'data.title' } },
      { path: 'chat', name: 'chat', component: () => import('@/views/ChatView.vue'), meta: { titleKey: 'chat.title' } },
      {
        path: 'accounts',
        name: 'accounts',
        component: () => import('@/views/AccountsView.vue'),
        meta: { titleKey: 'accounts.title', requiredCapability: CAP_ACCOUNT_MANAGE },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async to => {
  const authStore = useAuthStore()
  const token = authStore.token || localStorage.getItem('token')
  if (to.meta.requiresAuth !== false && !token) {
    return { name: 'login' }
  }

  if (token && !authStore.isAuthenticated) {
    await authStore.ensureInitialized()
  }

  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    return { name: 'login' }
  }

  const requiredCapability = typeof to.meta.requiredCapability === 'string'
    ? to.meta.requiredCapability
    : ''
  if (requiredCapability && !authStore.capabilities.includes(requiredCapability)) {
    authStore.handleForbidden()
    return { name: 'login' }
  }

  if ((to.name === 'login' || to.name === 'register') && authStore.isAuthenticated) {
    return { name: 'dashboard' }
  }

  return undefined
})

export default router
