import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, titleKey: 'login.submit' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { titleKey: 'dashboard.title' } },
      { path: 'plugins', name: 'plugins', component: () => import('@/views/PluginsView.vue'), meta: { titleKey: 'plugins.title' } },
      { path: 'permissions', name: 'permissions', component: () => import('@/views/PermissionsView.vue'), meta: { titleKey: 'permissions.title' } },
      { path: 'groups', name: 'groups', component: () => import('@/views/GroupsView.vue'), meta: { titleKey: 'groups.title' } },
      { path: 'logs', name: 'logs', component: () => import('@/views/LogsView.vue'), meta: { titleKey: 'logs.title' } },
      { path: 'data', name: 'data', component: () => import('@/views/DataView.vue'), meta: { titleKey: 'data.title' } },
      { path: 'chat', name: 'chat', component: () => import('@/views/ChatView.vue'), meta: { titleKey: 'chat.title' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth !== false && !token) {
    return { name: 'login' }
  }
})

export default router
