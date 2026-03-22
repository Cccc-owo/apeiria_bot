<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">{{ t('logs.title') }}</h1>
      <v-spacer />
      <v-btn
        :icon="connected ? 'mdi-connection' : 'mdi-lan-disconnect'"
        :color="connected ? 'success' : 'error'"
        variant="text"
        @click="toggleConnection"
      />
      <v-btn icon="mdi-delete-sweep" variant="text" @click="logs = []" />
    </div>

    <v-card class="log-card pa-4" style="min-height: 60vh">
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
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  background:
    linear-gradient(180deg, rgba(var(--v-theme-primary), 0.04), transparent 120px),
    rgba(var(--v-theme-surface), 0.9);
}

.log-container {
  max-height: 70vh;
  overflow-y: auto;
  font-family: ui-monospace, SFMono-Regular, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.86);
}
</style>
