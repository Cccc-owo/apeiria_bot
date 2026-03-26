<template>
  <v-app class="app-root">
    <router-view />
  </v-app>
</template>

<script setup lang="ts">
  import { computed, onMounted, watchEffect } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
  import { getCurrentUser } from '@/api'
  import { useAuthStore } from '@/stores/auth'

  const route = useRoute()
  const { t, locale } = useI18n()
  const authStore = useAuthStore()

  const documentTitle = computed(() => {
    const titleKey = typeof route.meta.titleKey === 'string' ? route.meta.titleKey : ''
    if (!titleKey) {
      return t('layout.defaultTitle')
    }
    return t('layout.pageTitle', { page: t(titleKey) })
  })

  watchEffect(() => {
    document.title = documentTitle.value
    document.documentElement.lang = locale.value === 'zh_CN' ? 'zh-CN' : 'en-US'
  })

  onMounted(async () => {
    if (!authStore.token) {
      return
    }
    if (authStore.principal) {
      return
    }
    try {
      const response = await getCurrentUser()
      authStore.setPrincipal(response.data)
    } catch {
      authStore.logout()
    }
  })
</script>

<style scoped>
.app-root {
  background: rgb(var(--v-theme-background));
}
</style>
