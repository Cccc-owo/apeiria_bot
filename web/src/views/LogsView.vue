<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('logs.title') }}</h1>
      <div class="page-actions">
        <v-chip :color="connected ? 'success' : 'error'" variant="tonal">
          {{ connected ? t('logs.connected') : t('logs.disconnected') }}
        </v-chip>
        <v-btn
          :prepend-icon="connected ? 'mdi-lan-disconnect' : 'mdi-connection'"
          variant="tonal"
          @click="toggleConnection"
        >
          {{ connected ? t('logs.disconnect') : t('logs.connect') }}
        </v-btn>
        <v-btn
          prepend-icon="mdi-delete-sweep"
          variant="text"
          :disabled="logs.length === 0"
          @click="logs = []"
        >
          {{ t('logs.clear') }}
        </v-btn>
      </div>
    </div>

    <v-card class="log-card page-panel">
      <div ref="logContainer" class="log-container">
        <div v-for="(line, i) in logs" :key="i" :class="logClass(line)">
          {{ line }}
        </div>
        <div v-if="logs.length === 0" class="text-medium-emphasis text-center pa-8">
          {{ t('logs.waiting') }}
        </div>
      </div>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const logs = ref<string[]>([])
const connected = ref(false)
const logContainer = ref<HTMLElement>()
const { t } = useI18n()
let ws: WebSocket | null = null

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/api/logs/ws`)

  ws.onopen = () => {
    const token = localStorage.getItem('token')
    if (token) ws?.send(token)
    connected.value = true
  }

  ws.onmessage = (e) => {
    logs.value.push(e.data)
    if (logs.value.length > 1000) logs.value.splice(0, 100)
    nextTick(() => {
      logContainer.value?.scrollTo(0, logContainer.value.scrollHeight)
    })
  }

  ws.onclose = () => { connected.value = false }
}

function disconnect() {
  ws?.close()
  ws = null
  connected.value = false
}

function toggleConnection() {
  connected.value ? disconnect() : connect()
}

function logClass(line: string) {
  if (line.includes('ERROR')) return 'text-error'
  if (line.includes('WARNING')) return 'text-warning'
  if (line.includes('SUCCESS')) return 'text-success'
  return ''
}

onMounted(connect)
onUnmounted(disconnect)
</script>

<style scoped>
.log-card {
  background: rgb(var(--v-theme-surface-container-low));
  min-height: 60vh;
}

.log-container {
  padding: 14px 16px;
  max-height: 70vh;
  overflow-y: auto;
  font-family: ui-monospace, SFMono-Regular, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
  font-size: 12.5px;
  line-height: 1.52;
  color: rgba(var(--v-theme-on-surface), 0.86);
}
</style>
