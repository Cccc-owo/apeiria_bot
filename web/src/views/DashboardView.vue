<template>
  <div class="d-flex flex-column ga-6">
    <div class="d-flex align-center justify-space-between flex-wrap ga-3">
      <h1 class="text-h4">{{ t('dashboard.title') }}</h1>
      <div class="d-flex flex-wrap ga-2">
        <v-btn color="warning" variant="tonal" :loading="restarting" @click="handleRestart">
          {{ t('dashboard.restart') }}
        </v-btn>
        <v-btn variant="tonal" :loading="loading" @click="loadStatus">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert
      v-if="status"
      type="info"
      variant="tonal"
      density="comfortable"
    >
      {{ t('dashboard.summary', {
        plugins: status.plugins_count,
        adapters: status.adapters.length,
        groups: status.groups_count,
      }) }}
    </v-alert>

    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" :color="statusColor" class="mr-4">{{ statusIcon }}</v-icon>
            <div>
              <div class="text-overline">{{ t('dashboard.status') }}</div>
              <div class="text-h5">{{ status?.status || '...' }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="primary" class="mr-4">mdi-clock-outline</v-icon>
            <div>
              <div class="text-overline">{{ t('dashboard.uptime') }}</div>
              <div class="text-h5">{{ formatUptime(status?.uptime) }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="accent" class="mr-4">mdi-puzzle</v-icon>
            <div>
              <div class="text-overline">{{ t('dashboard.plugins') }}</div>
              <div class="text-h5">{{ status?.plugins_count ?? '...' }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="info" class="mr-4">mdi-connection</v-icon>
            <div>
              <div class="text-overline">{{ t('dashboard.adapters') }}</div>
              <div class="text-h5">{{ status?.adapters?.length ?? '...' }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card v-if="status?.adapters?.length" variant="outlined">
      <v-card-text class="d-flex flex-column ga-3">
        <div class="text-subtitle-2 font-weight-medium">{{ t('dashboard.adapterList') }}</div>
        <div class="d-flex flex-wrap ga-2">
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

    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text>
            <div class="text-overline">{{ t('dashboard.disabledPlugins') }}</div>
            <div class="text-h5">{{ status?.disabled_plugins_count ?? '...' }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text>
            <div class="text-overline">{{ t('dashboard.groups') }}</div>
            <div class="text-h5">{{ status?.groups_count ?? '...' }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text>
            <div class="text-overline">{{ t('dashboard.disabledGroups') }}</div>
            <div class="text-h5">{{ status?.disabled_groups_count ?? '...' }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card variant="outlined">
          <v-card-text>
            <div class="text-overline">{{ t('dashboard.bans') }}</div>
            <div class="text-h5">{{ status?.bans_count ?? '...' }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getStatus, restartBot } from '@/api'
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
    const message = error instanceof Error ? error.message : t('dashboard.restartFailed')
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
