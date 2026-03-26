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

    <div class="logs-quick-filters">
      <v-chip
        v-for="level in quickLevelFilters"
        :key="level"
        size="small"
        :variant="selectedLevels.includes(level) ? 'flat' : 'tonal'"
        :color="levelColor(level)"
        class="logs-quick-filters__chip"
        @click="toggleQuickLevel(level)"
      >
        {{ level }}
      </v-chip>
      <v-btn
        v-if="selectedLevels.length"
        size="small"
        variant="text"
        class="logs-quick-filters__reset"
        @click="selectedLevels = []"
      >
        {{ t('logs.resetLevels') }}
      </v-btn>
    </div>

    <div class="page-summary-grid mb-4">
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('logs.totalCount') }}</div>
        <div class="summary-card__value">{{ logs.length }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('logs.visibleCount') }}</div>
        <div class="summary-card__value">{{ filteredLogs.length }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('logs.errorCount') }}</div>
        <div class="summary-card__value">{{ highSignalCount }}</div>
      </v-sheet>
    </div>

    <v-card class="page-panel log-card">
      <div v-if="hasMoreHistory || loadingOlder" class="log-card__history">
        <v-btn
          variant="text"
          size="small"
          :loading="loadingOlder"
          @click="loadOlderHistory"
        >
          {{ t('logs.loadOlder') }}
        </v-btn>
      </div>

      <div v-if="filteredLogs.length > 0" class="log-table-head">
        <span>{{ t('logs.level') }}</span>
        <span>{{ t('logs.timestamp') }}</span>
        <span>{{ t('logs.source') }}</span>
        <span>{{ t('logs.message') }}</span>
        <span></span>
      </div>

      <div v-if="filteredLogs.length === 0" class="text-medium-emphasis text-center pa-8">
        {{ loadingHistory ? t('common.loading') : logs.length === 0 ? t('logs.waiting') : t('logs.noResults') }}
      </div>

      <div v-else ref="logContainer" class="structured-log-list" @scroll="handleLogScroll">
        <v-expansion-panels variant="accordion">
          <v-expansion-panel
            v-for="entry in filteredLogs"
            :key="entry.id"
            :class="`log-entry log-entry--${entry.level.toLowerCase()}`"
          >
            <v-expansion-panel-title v-slot="{ expanded }" hide-actions>
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
                <span class="log-entry__source" :title="entry.source">{{ entry.source }}</span>
                <span class="log-entry__message">{{ entry.message }}</span>
                <span class="log-entry__toggle" aria-hidden="true">
                  <v-icon size="18">
                    {{ expanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
                  </v-icon>
                </span>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div class="log-entry__details">
                <div class="text-caption text-medium-emphasis">{{ t('logs.raw') }}</div>
                <pre class="log-entry__raw">{{ entry.raw }}</pre>
                <div v-if="Object.keys(entry.extra).length" class="text-caption text-medium-emphasis">
                  {{ t('logs.extra') }}
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
import { nextTick, onActivated, onDeactivated, onMounted, onUnmounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLogHistory } from '@/api'
import type { LogItem } from '@/api'

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
const loadingHistory = ref(false)
const loadingOlder = ref(false)
const hasMoreHistory = ref(false)
const nextBefore = ref<number | null>(0)
const { t } = useI18n()
let ws: WebSocket | null = null
const quickLevelFilters = ['ERROR', 'WARNING', 'INFO']

const levelOptions = computed(() => Array.from(new Set(logs.value.map((item) => item.level))).sort())
const sourceOptions = computed(() => Array.from(new Set(logs.value.map((item) => item.source))).sort())
const highSignalCount = computed(() =>
  logs.value.filter((entry) => entry.level === 'ERROR' || entry.level === 'CRITICAL' || entry.level === 'WARNING').length,
)
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
  disconnect()
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/api/logs/ws`)

  ws.onopen = () => {
    const token = localStorage.getItem('token')
    if (token) ws?.send(token)
    connected.value = true
  }

  ws.onmessage = (event) => {
    logs.value.push(normalizeLogFrame(event.data))
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

function resetLogsView() {
  logs.value = []
  selectedLevels.value = []
  selectedSources.value = []
  search.value = ''
  hasMoreHistory.value = false
  nextBefore.value = 0
}

function toLogEntry(item: LogItem): LogEntry {
  return {
    timestamp: item.timestamp,
    level: item.level,
    source: item.source,
    message: item.message,
    raw: item.raw,
    extra: item.extra,
    id: `${item.timestamp}_${item.level}_${item.source}_${Math.random().toString(16).slice(2)}`,
  }
}

async function loadInitialHistory() {
  loadingHistory.value = true
  try {
    const response = await getLogHistory({ before: 0, limit: 50 })
    logs.value = response.data.items
      .slice()
      .reverse()
      .map(item => toLogEntry(item))
    hasMoreHistory.value = response.data.has_more
    nextBefore.value = response.data.next_before
    await nextTick()
    logContainer.value?.scrollTo({ top: logContainer.value.scrollHeight })
  } finally {
    loadingHistory.value = false
  }
}

async function loadOlderHistory() {
  if (loadingOlder.value || nextBefore.value === null) return
  const container = logContainer.value
  const previousHeight = container?.scrollHeight || 0
  loadingOlder.value = true
  try {
    const response = await getLogHistory({ before: nextBefore.value, limit: 50 })
    const olderEntries = response.data.items
      .slice()
      .reverse()
      .map(item => toLogEntry(item))
    logs.value = [...olderEntries, ...logs.value]
    hasMoreHistory.value = response.data.has_more
    nextBefore.value = response.data.next_before
    await nextTick()
    if (container) {
      const nextHeight = container.scrollHeight
      container.scrollTop = nextHeight - previousHeight
    }
  } finally {
    loadingOlder.value = false
  }
}

function handleLogScroll(event: Event) {
  const target = event.target as HTMLElement | null
  if (!target || loadingOlder.value || !hasMoreHistory.value) {
    return
  }
  if (target.scrollTop <= 24) {
    void loadOlderHistory()
  }
}

async function initializeLogsView() {
  resetLogsView()
  try {
    await loadInitialHistory()
  } finally {
    connect()
  }
}

async function toggleConnection() {
  if (connected.value) {
    disconnect()
    return
  }
  if (logs.value.length === 0) {
    await loadInitialHistory()
  }
  connect()
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

function toggleQuickLevel(level: string) {
  if (selectedLevels.value.includes(level)) {
    selectedLevels.value = selectedLevels.value.filter(item => item !== level)
    return
  }
  selectedLevels.value = [...selectedLevels.value, level]
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

onMounted(() => { void initializeLogsView() })
onActivated(() => { void initializeLogsView() })
onDeactivated(disconnect)
onUnmounted(disconnect)
</script>

<style scoped>
.log-card {
  background: rgb(var(--v-theme-surface-container-low));
  min-height: 60vh;
}

.log-card__history {
  display: flex;
  justify-content: center;
  padding: 10px 12px 0;
}

.logs-filter {
  min-width: 180px;
}

.structured-log-list {
  max-height: 70vh;
  overflow-y: auto;
  padding: 0 12px 12px;
}

.logs-quick-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.logs-quick-filters__chip {
  cursor: pointer;
}

.logs-quick-filters__reset {
  min-width: 0;
}

.log-table-head {
  display: grid;
  grid-template-columns: 110px 176px 220px minmax(0, 1fr) 28px;
  gap: 12px;
  align-items: center;
  padding: 12px 20px 10px;
  margin: 0 12px;
  border-bottom: 1px solid rgba(var(--v-theme-outline-variant), 0.5);
  background: rgb(var(--v-theme-surface-container-low));
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
  grid-template-columns: 110px 176px 220px minmax(0, 1fr) 28px;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-width: 0;
}

.log-entry__time,
.log-entry__source {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.log-entry__toggle {
  display: inline-flex;
  justify-content: center;
  color: rgba(var(--v-theme-on-surface), 0.52);
}

:deep(.log-entry .v-expansion-panel-title) {
  min-height: 62px;
  padding: 14px 18px;
}

:deep(.log-entry .v-expansion-panel-title__overlay) {
  opacity: 0 !important;
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

  .log-entry__toggle {
    justify-content: flex-start;
  }
}
</style>
