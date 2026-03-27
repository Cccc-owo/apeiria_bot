<template>
  <v-app class="app-root">
    <div v-if="!authStore.isReady" class="app-loading">
      {{ t('common.loading') }}
    </div>
    <router-view v-else />
  </v-app>
</template>

<script setup lang="ts">
  import { computed, onMounted, watchEffect } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
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
    await authStore.initialize()
  })
</script>

<style scoped>
.app-root {
  background: rgb(var(--v-theme-background));
}

.app-loading {
  display: grid;
  min-height: 100vh;
  place-items: center;
}
</style>
