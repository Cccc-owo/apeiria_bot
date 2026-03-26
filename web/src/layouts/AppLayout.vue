<template>
  <v-navigation-drawer
    v-model="drawer"
    class="app-drawer"
    :class="{ 'app-drawer--rail': rail }"
    permanent
    :rail="rail"
    :rail-width="56"
    :width="208"
  >
    <div class="app-drawer__header">
      <v-list-item
        v-if="!rail"
        class="app-drawer__brand"
        nav
        prepend-icon="mdi-robot-happy"
        :subtitle="t('layout.subtitle')"
        :title="t('layout.brand')"
      />
      <v-btn
        class="app-drawer__toggle"
        :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
        size="small"
        variant="text"
        @click="rail = !rail"
      />
    </div>

    <v-divider />

    <div class="app-drawer__nav">
      <div v-if="!rail" class="app-drawer__section-label">{{ t('layout.navigation') }}</div>
      <v-list class="app-drawer__list" density="compact" nav>
        <v-list-item
          v-for="item in navItems"
          :key="item.to"
          :prepend-icon="item.icon"
          rounded="lg"
          :title="item.title"
          :to="item.to"
        />
      </v-list>
    </div>

    <template #append>
      <div class="app-drawer__footer">
        <div v-if="!rail" class="app-drawer__section-label">{{ t('layout.systemSection') }}</div>
        <v-list class="app-drawer__list" density="compact" nav>
          <v-list-item
            prepend-icon="mdi-account-circle-outline"
            rounded="lg"
            :subtitle="authStore.principal?.role || t('layout.adminRole')"
            :title="authStore.principal?.username || t('layout.unknownUser')"
          />
          <v-menu location="top" offset="8">
            <template #activator="{ props }">
              <v-list-item
                v-bind="props"
                prepend-icon="mdi-translate"
                rounded="lg"
                :subtitle="currentLocaleLabel"
                :title="t('layout.language')"
              />
            </template>
            <v-list class="locale-menu" density="compact">
              <v-list-item
                :active="locale === 'zh_CN'"
                rounded="lg"
                :title="t('layout.chinese')"
                @click="setLocale('zh_CN')"
              />
              <v-list-item
                :active="locale === 'en_US'"
                rounded="lg"
                :title="t('layout.english')"
                @click="setLocale('en_US')"
              />
            </v-list>
          </v-menu>
          <v-list-item
            prepend-icon="mdi-theme-light-dark"
            rounded="lg"
            :subtitle="themeToggleSubtitle"
            :title="themeToggleLabel"
            @click="toggleTheme"
          />
          <v-list-item
            prepend-icon="mdi-logout"
            rounded="lg"
            :title="t('layout.logout')"
            @click="handleLogout"
          />
        </v-list>
      </div>
    </template>
  </v-navigation-drawer>

  <v-main class="app-main">
    <v-container class="app-container" fluid>
      <router-view />
    </v-container>
  </v-main>

  <v-snackbar
    v-model="noticeStore.visible"
    :color="noticeStore.color"
    location="top right"
    timeout="2400"
  >
    {{ noticeStore.message }}
  </v-snackbar>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute, useRouter } from 'vue-router'
  import { useTheme } from 'vuetify'
  import { useAuthStore } from '@/stores/auth'
  import { useNoticeStore } from '@/stores/notice'
  import type { SupportedLocale } from '@/plugins/i18n'

  const drawer = ref(true)
  const rail = ref(false)
  const { t, locale } = useI18n()
  const theme = useTheme()
  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()
  const noticeStore = useNoticeStore()

  const navItems = computed(() => [
    { icon: 'mdi-view-dashboard', title: t('layout.dashboard'), to: '/dashboard' },
    { icon: 'mdi-puzzle', title: t('layout.plugins'), to: '/core' },
    { icon: 'mdi-shield-account', title: t('layout.permissions'), to: '/permissions' },
    { icon: 'mdi-account-group', title: t('layout.groups'), to: '/groups' },
    { icon: 'mdi-database-outline', title: t('layout.data'), to: '/data' },
    { icon: 'mdi-chat-outline', title: t('layout.chat'), to: '/chat' },
    { icon: 'mdi-text-box-outline', title: t('layout.logs'), to: '/logs' },
  ])

  const themeToggleLabel = computed(() => theme.global.current.value.dark ? t('layout.toLight') : t('layout.toDark'))
  const themeToggleSubtitle = computed(() => theme.global.current.value.dark ? t('layout.darkTheme') : t('layout.lightTheme'))
  const currentLocaleLabel = computed(() => (
    locale.value === 'zh_CN' ? t('layout.chinese') : t('layout.english')
  ))

  function toggleTheme () {
    const nextTheme = theme.global.current.value.dark ? 'light' : 'dark'
    theme.global.name.value = nextTheme
    localStorage.setItem('apeiria-theme', nextTheme)
  }

  function setLocale (nextLocale: SupportedLocale) {
    if (locale.value === nextLocale) {
      return
    }
    locale.value = nextLocale
    localStorage.setItem('apeiria-locale', locale.value)

    const titleKey = typeof route.meta.titleKey === 'string' ? route.meta.titleKey : ''
    document.title = titleKey
      ? t('layout.pageTitle', { page: t(titleKey) })
      : t('layout.defaultTitle')
    document.documentElement.lang = locale.value === 'zh_CN' ? 'zh-CN' : 'en-US'
  }

  function handleLogout () {
    authStore.logout()
    router.push('/login')
  }
</script>

<style scoped>
.app-drawer {
  position: relative;
  background: rgb(var(--v-theme-surface));
  box-shadow: inset -1px 0 0 rgba(var(--v-theme-outline-variant), 0.72);
}

.app-drawer__header {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 4px 4px;
}

.app-drawer__toggle {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  margin-top: 2px;
}

.app-drawer__brand {
  flex: 1;
  min-width: 0;
}

.app-drawer__brand:deep(.v-list-item) {
  padding-inline: 4px !important;
}

.app-drawer__brand:deep(.v-list-item__prepend) {
  margin-inline-end: 10px !important;
}

.app-drawer__brand:deep(.v-list-item-title) {
  font-size: 0.98rem;
  line-height: 1.1;
  white-space: nowrap;
}

.app-drawer__brand:deep(.v-list-item-subtitle) {
  display: -webkit-box;
  overflow: hidden;
  line-height: 1.1;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.app-drawer__nav,
.app-drawer__footer {
  padding: 6px 6px;
}

.app-drawer__list {
  padding: 0;
  background: transparent;
}

.app-drawer__section-label {
  padding: 4px 10px 6px;
  color: rgba(var(--v-theme-on-surface), 0.46);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.app-drawer__section-label--spaced {
  margin-top: 6px;
}

.app-drawer__footer {
  padding-top: 10px;
  padding-bottom: 8px;
  box-shadow: inset 0 1px 0 rgba(var(--v-theme-outline-variant), 0.52);
}

.app-drawer--rail .app-drawer__header {
  justify-content: center;
  align-items: center;
  padding: 6px 0 4px;
}

.app-drawer--rail .app-drawer__brand {
  display: none;
}

.app-drawer--rail .app-drawer__toggle {
  margin-top: 0;
}

.app-drawer--rail .app-drawer__nav,
.app-drawer--rail .app-drawer__footer {
  padding-left: 0;
  padding-right: 0;
}

.app-main {
  min-height: 100vh;
  background: rgb(var(--v-theme-background));
  transition: background-color 0.2s ease, color 0.2s ease;
}

.app-container {
  padding: var(--page-gutter);
}

.locale-menu {
  min-width: 144px;
}

@media (max-width: 960px) {
  .app-container {
    padding: 16px;
  }
}
</style>
