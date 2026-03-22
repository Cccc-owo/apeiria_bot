<template>
  <v-navigation-drawer v-model="drawer" :rail="rail" permanent class="app-drawer">
    <v-list-item
      prepend-icon="mdi-robot-happy"
      :title="t('layout.brand')"
      :subtitle="t('layout.subtitle')"
      nav
    >
      <template #append>
        <v-btn
          :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          variant="text"
          size="small"
          @click="rail = !rail"
        />
      </template>
    </v-list-item>

    <v-divider />

    <v-list density="compact" nav>
      <v-list-item
        v-for="item in navItems"
        :key="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        :to="item.to"
        rounded="lg"
      />
    </v-list>

    <template #append>
      <v-list density="compact" nav>
        <v-menu location="top" offset="8">
          <template #activator="{ props }">
            <v-list-item
              v-bind="props"
              prepend-icon="mdi-translate"
              :title="t('layout.language')"
              :subtitle="currentLocaleLabel"
              rounded="lg"
            />
          </template>
          <v-list density="compact" class="locale-menu">
            <v-list-item
              :active="locale === 'zh_CN'"
              :title="t('layout.chinese')"
              rounded="lg"
              @click="setLocale('zh_CN')"
            />
            <v-list-item
              :active="locale === 'en_US'"
              :title="t('layout.english')"
              rounded="lg"
              @click="setLocale('en_US')"
            />
          </v-list>
        </v-menu>
        <v-list-item
          prepend-icon="mdi-theme-light-dark"
          :title="themeToggleLabel"
          :subtitle="themeToggleSubtitle"
          @click="toggleTheme"
          rounded="lg"
        />
        <v-list-item
          prepend-icon="mdi-logout"
          :title="t('layout.logout')"
          @click="handleLogout"
          rounded="lg"
        />
      </v-list>
    </template>
  </v-navigation-drawer>

  <v-main class="app-main">
    <v-container fluid class="app-container">
      <router-view />
    </v-container>
  </v-main>

  <v-snackbar
    v-model="noticeStore.visible"
    :color="noticeStore.color"
    timeout="2400"
    location="top right"
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
  { icon: 'mdi-puzzle', title: t('layout.plugins'), to: '/plugins' },
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

function toggleTheme() {
  const nextTheme = theme.global.current.value.dark ? 'light' : 'dark'
  theme.global.name.value = nextTheme
  localStorage.setItem('apeiria-theme', nextTheme)
}

function setLocale(nextLocale: SupportedLocale) {
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

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-drawer {
  border-right: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  background:
    linear-gradient(180deg, rgba(var(--v-theme-primary), 0.08), transparent 180px),
    rgba(var(--v-theme-surface), 0.94);
  backdrop-filter: blur(18px);
}

.app-main {
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(var(--v-theme-primary), 0.12), transparent 28%),
    radial-gradient(circle at bottom left, rgba(var(--v-theme-secondary), 0.08), transparent 30%),
    rgb(var(--v-theme-background));
  transition: background-color 0.2s ease, color 0.2s ease;
}

.app-container {
  padding: 24px;
}

.locale-menu {
  min-width: 144px;
}
</style>
