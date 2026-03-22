<template>
  <div class="d-flex flex-column ga-6">
    <div class="d-flex align-center justify-space-between flex-wrap ga-3">
      <h1 class="text-h4">{{ t('dashboard.title') }}</h1>
      <v-btn variant="tonal" :loading="loading" @click="loadStatus">{{ t('common.refresh') }}</v-btn>
    </div>

    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="success" class="mr-4">mdi-check-circle</v-icon>
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
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getStatus } from '@/api'

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
const { t } = useI18n()

async function loadStatus() {
  loading.value = true
  try {
    const res = await getStatus()
    status.value = res.data
  } finally {
    loading.value = false
  }
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
