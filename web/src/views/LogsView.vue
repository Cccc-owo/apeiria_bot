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
          prepend-icon="mdi-download-outline"
          variant="text"
          :disabled="filteredLogs.length === 0"
          @click="exportLogs"
        >
          {{ t('logs.export') }}
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

    <div class="page-toolbar-form">
      <v-text-field
        v-model.trim="search"
        :label="t('logs.search')"
        density="compact"
        hide-details
        prepend-inner-icon="mdi-magnify"
      />
      <v-select
        v-model="selectedLevels"
        :items="levelOptions"
        :label="t('logs.level')"
        density="compact"
        hide-details
        chips
        multiple
        class="logs-filter"
      />
      <v-select
        v-model="selectedSources"
        :items="sourceOptions"
        :label="t('logs.source')"
        density="compact"
        hide-details
        chips
        multiple
        class="logs-filter"
      />
      <v-switch
        v-model="autoScroll"
        :label="t('logs.autoScroll')"
        color="primary"
        hide-details
        inset
      />
    </div>

    <v-card class="page-panel log-card">
      <div v-if="filteredLogs.length === 0" class="text-medium-emphasis text-center pa-8">
        {{ t('logs.waiting') }}
      </div>

      <div v-else ref="logContainer" class="structured-log-list">
        <div class="log-table-head">
          <span>{{ t('logs.level') }}</span>
          <span>{{ t('logs.timestamp') }}</span>
          <span>{{ t('logs.source') }}</span>
          <span>{{ t('logs.message') }}</span>
        </div>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel
            v-for="entry in filteredLogs"
            :key="entry.id"
            :class="`log-entry log-entry--${entry.level.toLowerCase()}`"
          >
            <v-expansion-panel-title>
              <div class="log-entry__summary">
                <v-chip
                  size="small"
                  variant="tonal"
                  :color="levelColor(entry.level)"
                  class="log-entry__level-chip"
                >
                  {{ entry.level }}
                </v-chip>
                <span class="log-entry__time">{{ entry.timestamp }}</span>
                <span class="log-entry__source">{{ entry.source }}</span>
                <span class="log-entry__message">{{ entry.message }}</span>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div class="log-entry__details">
                <div class="text-caption text-medium-emphasis">{{ t('logs.raw') }}</div>
                <pre class="log-entry__raw">{{ entry.raw }}</pre>
                <div v-if="Object.keys(entry.extra).length" class="text-caption text-medium-emphasis">
                  extra
                </div>
                <pre v-if="Object.keys(entry.extra).length" class="log-entry__raw">{{ JSON.stringify(entry.extra, null, 2) }}</pre>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface LogEntry {
  id: string
  timestamp: string
  level: string
  source: string
  message: string
  raw: string
  extra: Record<string, unknown>
}

const logs = ref<LogEntry[]>([])
const connected = ref(false)
const autoScroll = ref(true)
const search = ref('')
const selectedLevels = ref<string[]>([])
const selectedSources = ref<string[]>([])
const logContainer = ref<HTMLElement>()
const { t } = useI18n()
let ws: WebSocket | null = null

const levelOptions = computed(() => Array.from(new Set(logs.value.map((item) => item.level))).sort())
const sourceOptions = computed(() => Array.from(new Set(logs.value.map((item) => item.source))).sort())
const filteredLogs = computed(() => logs.value.filter((entry) => {
  if (selectedLevels.value.length > 0 && !selectedLevels.value.includes(entry.level)) {
    return false
  }
  if (selectedSources.value.length > 0 && !selectedSources.value.includes(entry.source)) {
    return false
  }
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) {
    return true
  }
  const haystack = `${entry.timestamp} ${entry.level} ${entry.source} ${entry.message} ${entry.raw} ${JSON.stringify(entry.extra)}`.toLowerCase()
  return haystack.includes(keyword)
}))

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/api/logs/ws`)

  ws.onopen = () => {
    const token = localStorage.getItem('token')
    if (token) ws?.send(token)
    connected.value = true
  }

  ws.onmessage = (event) => {
    logs.value.push(normalizeLogFrame(event.data))
    if (logs.value.length > 1000) logs.value.splice(0, 100)
    if (!autoScroll.value) {
      return
    }
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

function normalizeLogFrame(frame: string): LogEntry {
  try {
    const parsed = JSON.parse(frame) as Partial<LogEntry>
    return {
      id: `${parsed.timestamp || Date.now()}_${Math.random().toString(16).slice(2)}`,
      timestamp: parsed.timestamp || new Date().toISOString(),
      level: parsed.level || 'INFO',
      source: parsed.source || 'unknown',
      message: parsed.message || parsed.raw || frame,
      raw: parsed.raw || frame,
      extra: (parsed.extra && typeof parsed.extra === 'object') ? parsed.extra as Record<string, unknown> : {},
    }
  } catch {
    return {
      id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      timestamp: new Date().toISOString(),
      level: 'INFO',
      source: 'legacy',
      message: frame,
      raw: frame,
      extra: {},
    }
  }
}

function levelColor(level: string) {
  if (level === 'ERROR' || level === 'CRITICAL') return 'error'
  if (level === 'WARNING') return 'warning'
  if (level === 'SUCCESS') return 'success'
  return 'info'
}

function exportLogs() {
  const blob = new Blob(
    [filteredLogs.value.map((entry) => JSON.stringify(entry)).join('\n')],
    { type: 'application/jsonl;charset=utf-8' },
  )
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `apeiria-logs-${Date.now()}.jsonl`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(connect)
onUnmounted(disconnect)
</script>

<style scoped>
.log-card {
  background: rgb(var(--v-theme-surface-container-low));
  min-height: 60vh;
}

.logs-filter {
  min-width: 180px;
}

.structured-log-list {
  max-height: 70vh;
  overflow-y: auto;
  padding: 12px;
}

.log-table-head {
  display: grid;
  grid-template-columns: 110px 176px 220px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 0 20px 10px 20px;
  color: rgba(var(--v-theme-on-surface), 0.56);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.log-entry {
  margin-bottom: 8px;
}

.log-entry__summary {
  display: grid;
  grid-template-columns: 110px 176px 220px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  width: 100%;
  min-width: 0;
}

.log-entry__time,
.log-entry__source {
  min-width: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
  font-size: 0.82rem;
  color: rgba(var(--v-theme-on-surface), 0.64);
}

.log-entry__level-chip {
  width: 96px;
  justify-content: center;
  font-weight: 700;
}

.log-entry__message {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

:deep(.log-entry .v-expansion-panel-title) {
  min-height: 62px;
  padding: 14px 18px;
}

:deep(.log-entry .v-expansion-panel-title__overlay) {
  opacity: 0 !important;
}

:deep(.log-entry .v-expansion-panel-title__icon) {
  margin-inline-start: 10px;
}

:deep(.log-entry .v-expansion-panel-text__wrapper) {
  padding-top: 0;
}

.log-entry__details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 18px 18px;
}

.log-entry__raw {
  margin: 0;
  padding: 12px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
  font-size: 12px;
}

@media (max-width: 960px) {
  .log-table-head {
    display: none;
  }

  .log-entry__summary {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .log-entry__message {
    white-space: normal;
  }
}
</style>
