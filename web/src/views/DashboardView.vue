<template>
  <div class="dashboard-view page-view">
    <section class="dashboard-hero">
      <div class="dashboard-hero__top">
        <div class="dashboard-hero__intro">
          <span class="text-overline dashboard-kicker">Apeiria Console</span>
          <h1 class="page-title">{{ t('dashboard.title') }}</h1>
          <div class="text-caption text-medium-emphasis">
            {{ lastUpdatedText }}
          </div>
        </div>
        <div class="page-actions">
          <v-switch
            v-model="autoRefresh"
            :label="t('dashboard.autoRefresh')"
            color="primary"
            hide-details
            inset
          />
          <v-btn color="warning" variant="tonal" :loading="restarting" @click="handleRestart">
            {{ t('dashboard.restart') }}
          </v-btn>
          <v-btn variant="tonal" :loading="loading" @click="refreshDashboard">
            {{ t('common.refresh') }}
          </v-btn>
        </div>
      </div>
    </section>

    <section class="dashboard-section">
      <div class="dashboard-section__header">
        <div class="dashboard-section__title">概览</div>
      </div>
      <v-row class="dashboard-overview">
        <v-col cols="12" sm="6" md="3">
          <v-card class="metric-card metric-card--status">
            <v-card-text class="metric-card__body">
              <div class="metric-card__topline">
                <div class="metric-card__label">{{ t('dashboard.status') }}</div>
                <div class="metric-card__icon" :class="`metric-card__icon--${statusColor}`">
                  <v-icon size="28">{{ statusIcon }}</v-icon>
                </div>
              </div>
              <div class="metric-card__value metric-card__value--status">{{ status?.status || '...' }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card class="metric-card">
            <v-card-text class="metric-card__body">
              <div class="metric-card__topline">
                <div class="metric-card__label">{{ t('dashboard.uptime') }}</div>
                <div class="metric-card__icon metric-card__icon--primary">
                  <v-icon size="28">mdi-clock-outline</v-icon>
                </div>
              </div>
              <div class="metric-card__value">{{ formatUptime(status?.uptime) }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card class="metric-card">
            <v-card-text class="metric-card__body">
              <div class="metric-card__topline">
                <div class="metric-card__label">{{ t('dashboard.plugins') }}</div>
                <div class="metric-card__icon metric-card__icon--accent">
                  <v-icon size="28">mdi-puzzle</v-icon>
                </div>
              </div>
              <div class="metric-card__value metric-card__value--number">{{ status?.plugins_count ?? '...' }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card class="metric-card">
            <v-card-text class="metric-card__body">
              <div class="metric-card__topline">
                <div class="metric-card__label">{{ t('dashboard.adapters') }}</div>
                <div class="metric-card__icon metric-card__icon--info">
                  <v-icon size="28">mdi-connection</v-icon>
                </div>
              </div>
              <div class="metric-card__value metric-card__value--number">{{ status?.adapters?.length ?? '...' }}</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </section>

    <section class="dashboard-grid">
      <v-card v-if="status?.adapters?.length" class="surface-card dashboard-grid__main">
        <v-card-text class="d-flex flex-column ga-3">
          <div class="surface-card__title">{{ t('dashboard.adapterList') }}</div>
          <div class="dashboard-adapter-list">
            <v-chip
              v-for="adapter in status.adapters"
              :key="adapter"
              size="small"
              variant="tonal"
              color="info"
            >
              {{ adapter }}
            </v-chip>
          </div>
        </v-card-text>
      </v-card>

      <div class="dashboard-grid__side">
        <div class="dashboard-section__header dashboard-section__header--tight">
          <div class="dashboard-section__title">附加统计</div>
        </div>
        <v-row>
          <v-col cols="12" sm="6" md="6">
            <v-card class="compact-metric-card">
              <v-card-text class="compact-metric-card__body">
                <div class="compact-metric-card__label">{{ t('dashboard.disabledPlugins') }}</div>
                <div class="compact-metric-card__value">{{ status?.disabled_plugins_count ?? '...' }}</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" sm="6" md="6">
            <v-card class="compact-metric-card">
              <v-card-text class="compact-metric-card__body">
                <div class="compact-metric-card__label">{{ t('dashboard.groups') }}</div>
                <div class="compact-metric-card__value">{{ status?.groups_count ?? '...' }}</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" sm="6" md="6">
            <v-card class="compact-metric-card">
              <v-card-text class="compact-metric-card__body">
                <div class="compact-metric-card__label">{{ t('dashboard.disabledGroups') }}</div>
                <div class="compact-metric-card__value">{{ status?.disabled_groups_count ?? '...' }}</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" sm="6" md="6">
            <v-card class="compact-metric-card">
              <v-card-text class="compact-metric-card__body">
                <div class="compact-metric-card__label">{{ t('dashboard.bans') }}</div>
                <div class="compact-metric-card__value">{{ status?.bans_count ?? '...' }}</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </div>
    </section>

    <section class="dashboard-section">
      <div class="dashboard-section__header">
        <div class="dashboard-section__title">{{ t('dashboard.recentEvents') }}</div>
      </div>
      <v-card class="page-panel dashboard-events-card">
        <div v-if="recentEvents.length === 0" class="pa-6 text-body-2 text-medium-emphasis text-center">
          {{ t('dashboard.noEvents') }}
        </div>
        <div v-else class="dashboard-events-list">
          <article
            v-for="event in recentEvents"
            :key="`${event.timestamp}:${event.source}:${event.message}`"
            class="dashboard-event"
          >
            <div class="dashboard-event__badge">
              <v-chip
                size="small"
                variant="tonal"
                :color="eventColor(event.level)"
                class="dashboard-event__chip"
              >
                {{ event.level }}
              </v-chip>
            </div>
            <div class="dashboard-event__content">
              <div class="dashboard-event__title">{{ event.message }}</div>
              <div class="dashboard-event__meta">
                <span>{{ event.timestamp }}</span>
                <span>{{ t('dashboard.eventSource') }}: {{ event.source }}</span>
              </div>
            </div>
          </article>
        </div>
      </v-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DashboardEventItem, DashboardStatus } from '@/api'
import { getDashboardEvents, getStatus, restartBot } from '@/api'
import { getErrorMessage } from '@/api/client'
import { useNoticeStore } from '@/stores/notice'

const status = ref<DashboardStatus | null>(null)
const recentEvents = ref<DashboardEventItem[]>([])
const loading = ref(false)
const restarting = ref(false)
const autoRefresh = ref(true)
const lastUpdatedAt = ref<Date | null>(null)
const { t, locale } = useI18n()
const noticeStore = useNoticeStore()
let refreshTimer: number | null = null

const statusColor = computed(() => status.value?.status === 'running' ? 'success' : 'warning')
const statusIcon = computed(() => status.value?.status === 'running' ? 'mdi-check-circle' : 'mdi-alert-circle')
const lastUpdatedText = computed(() => {
  if (!lastUpdatedAt.value) {
    return t('common.loading')
  }
  return t('dashboard.lastUpdated', {
    time: lastUpdatedAt.value.toLocaleTimeString(locale.value === 'zh_CN' ? 'zh-CN' : 'en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
  })
})

async function refreshDashboard () {
  loading.value = true
  try {
    const [statusResponse, eventsResponse] = await Promise.all([
      getStatus(),
      getDashboardEvents(),
    ])
    status.value = statusResponse.data
    recentEvents.value = eventsResponse.data.items
    lastUpdatedAt.value = new Date()
  } finally {
    loading.value = false
  }
}

async function handleRestart () {
  if (!window.confirm(t('dashboard.restartConfirm'))) return
  restarting.value = true
  try {
    const res = await restartBot()
    noticeStore.show(res.data.detail || t('dashboard.restartScheduled'), 'success')
    await waitForRestartTransition()
    window.location.reload()
  } catch (error) {
    const message = getErrorMessage(error, t('dashboard.restartFailed'))
    noticeStore.show(message, 'error')
  } finally {
    restarting.value = false
  }
}

async function waitForRestartTransition () {
  await waitForStatus(false, 30, 1000)
  await waitForStatus(true, 60, 1000)
}

async function waitForStatus (expectedOnline: boolean, maxAttempts: number, delayMs: number) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await sleep(delayMs)
    try {
      await getStatus()
      if (expectedOnline) return
    } catch {
      if (!expectedOnline) return
    }
  }

  throw new Error(t('dashboard.restartFailed'))
}

function sleep (ms: number) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

function formatUptime (seconds?: number): string {
  if (!seconds) return '...'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

function eventColor (level: string) {
  if (level === 'ERROR' || level === 'CRITICAL') return 'error'
  if (level === 'WARNING') return 'warning'
  return 'info'
}

function startAutoRefresh () {
  stopAutoRefresh()
  refreshTimer = window.setInterval(() => {
    void refreshDashboard()
  }, 15000)
}

function stopAutoRefresh () {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
}

watch(autoRefresh, enabled => {
  if (enabled) {
    startAutoRefresh()
    return
  }
  stopAutoRefresh()
})

onMounted(() => {
  void refreshDashboard()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.dashboard-view {
  padding-bottom: 8px;
}

.dashboard-hero__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.dashboard-hero__intro {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dashboard-hero {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  background: rgb(var(--v-theme-surface-container));
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 2px 8px rgba(15, 23, 42, 0.05);
}

.dashboard-kicker {
  color: rgba(var(--v-theme-on-surface), 0.64);
  letter-spacing: 0.08em !important;
}

.dashboard-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dashboard-section__header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dashboard-section__header--tight {
  margin-bottom: 4px;
}

.dashboard-section__title {
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.3;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 1fr);
  gap: 16px;
  align-items: start;
}

.dashboard-grid__side {
  display: flex;
  flex-direction: column;
}

.surface-card {
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
}

.dashboard-grid__main {
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 20px rgba(21, 101, 192, 0.08) !important;
}

.dashboard-adapter-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dashboard-event__title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.45;
  white-space: normal;
}

.dashboard-event__meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 4px;
  font-size: 0.85rem;
  color: rgba(var(--v-theme-on-surface), 0.62);
  white-space: normal;
}

.dashboard-events-card {
  background:
    linear-gradient(180deg, rgba(var(--v-theme-surface-container-high), 0.8), rgba(var(--v-theme-surface), 0.96));
}

.dashboard-events-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
}

.dashboard-event {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(var(--v-theme-background), 0.38);
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-outline-variant), 0.32);
}

.dashboard-event__badge {
  display: flex;
  justify-content: center;
  padding-top: 2px;
}

.dashboard-event__chip {
  min-width: 88px;
  justify-content: center;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.dashboard-event__content {
  min-width: 0;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-events-list {
    padding: 16px;
  }

  .dashboard-event {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .dashboard-event__badge {
    justify-content: flex-start;
  }
}
</style>
