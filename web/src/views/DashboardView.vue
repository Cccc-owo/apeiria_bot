<template>
  <div class="dashboard-view page-view">
    <section class="dashboard-hero">
      <div class="dashboard-hero__top">
        <div class="dashboard-hero__intro">
          <span class="text-overline dashboard-kicker">Apeiria Console</span>
          <h1 class="page-title">{{ t('dashboard.title') }}</h1>
        </div>
        <div class="page-actions">
          <v-btn color="warning" variant="tonal" :loading="restarting" @click="handleRestart">
            {{ t('dashboard.restart') }}
          </v-btn>
          <v-btn variant="tonal" :loading="loading" @click="loadStatus">{{ t('common.refresh') }}</v-btn>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getStatus, restartBot } from '@/api'
import { getErrorMessage } from '@/api/client'
import { useNoticeStore } from '@/stores/notice'

interface DashboardStatus {
  status: string
  uptime: number
  plugins_count: number
  disabled_plugins_count: number
  groups_count: number
  disabled_groups_count: number
  bans_count: number
  adapters: string[]
}

const status = ref<DashboardStatus | null>(null)
const loading = ref(false)
const restarting = ref(false)
const { t } = useI18n()
const noticeStore = useNoticeStore()

const statusColor = computed(() => status.value?.status === 'running' ? 'success' : 'warning')
const statusIcon = computed(() => status.value?.status === 'running' ? 'mdi-check-circle' : 'mdi-alert-circle')

async function loadStatus() {
  loading.value = true
  try {
    const res = await getStatus()
    status.value = res.data
  } finally {
    loading.value = false
  }
}

async function handleRestart() {
  if (!window.confirm(t('dashboard.restartConfirm'))) return
  restarting.value = true
  try {
    const res = await restartBot()
    noticeStore.show(res.data.detail || t('dashboard.restartScheduled'), 'success')
    await waitForRestart()
    window.location.reload()
  } catch (error) {
    const message = getErrorMessage(error, t('dashboard.restartFailed'))
    noticeStore.show(message, 'error')
  } finally {
    restarting.value = false
  }
}

async function waitForRestart() {
  const maxAttempts = 60
  const delayMs = 1000

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await sleep(delayMs)
    try {
      await getStatus()
      return
    } catch {
      continue
    }
  }

  throw new Error(t('dashboard.restartFailed'))
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function formatUptime(seconds?: number): string {
  if (!seconds) return '...'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

onMounted(() => {
  void loadStatus()
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

.compact-metric-card__label,
.surface-card__title {
  color: rgba(var(--v-theme-on-primary-container), 0.78);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

@media (max-width: 960px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-hero {
    padding: 14px;
    border-radius: 18px;
  }
}
</style>
