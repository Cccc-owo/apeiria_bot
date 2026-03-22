<template>
  <div class="d-flex flex-column ga-6">
    <div class="d-flex align-center justify-space-between flex-wrap ga-3">
      <h1 class="text-h4">{{ t('plugins.title') }}</h1>
      <v-btn variant="tonal" :loading="loading" @click="loadPlugins">{{ t('common.refresh') }}</v-btn>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="plugins"
        :loading="loading"
        density="comfortable"
      >
        <template #item.plugin_type="{ value }">
          <v-chip size="small" :color="typeColor(value)">{{ value }}</v-chip>
        </template>
        <template #item.source="{ value }">
          <v-chip size="small" variant="outlined" :color="sourceColor(value)">
            {{ sourceLabel(value) }}
          </v-chip>
        </template>
        <template #item.admin_level="{ value }">
          <v-chip size="small" variant="outlined">Lv.{{ value }}</v-chip>
        </template>
        <template #item.is_global_enabled="{ item }">
          <div class="plugin-enabled-cell">
            <v-switch
              :model-value="item.is_global_enabled"
              color="success"
              hide-details
              inset
              :disabled="item.is_protected"
              :loading="pendingModule === item.module_name"
              @update:model-value="togglePlugin(item, $event)"
            />
            <v-tooltip v-if="item.is_protected" location="top">
              <template #activator="{ props }">
                <v-chip
                  v-bind="props"
                  size="x-small"
                  color="warning"
                  variant="tonal"
                >
                  {{ t('plugins.protected') }}
                </v-chip>
              </template>
              {{ item.protected_reason }}
            </v-tooltip>
          </div>
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlugins, updatePlugin } from '@/api'
import { useNoticeStore } from '@/stores/notice'

interface PluginRow {
  module_name: string
  name: string | null
  description: string | null
  source: string
  plugin_type: string
  admin_level: number
  is_global_enabled: boolean
  version: string | null
  is_protected: boolean
  protected_reason: string | null
}

const plugins = ref<PluginRow[]>([])
const loading = ref(false)
const pendingModule = ref('')
const errorMessage = ref('')
const noticeStore = useNoticeStore()
const { t } = useI18n()

const headers = computed(() => [
  { title: t('plugins.name'), key: 'name' },
  { title: t('plugins.module'), key: 'module_name' },
  { title: t('plugins.source'), key: 'source' },
  { title: t('plugins.type'), key: 'plugin_type' },
  { title: t('plugins.level'), key: 'admin_level' },
  { title: t('plugins.enabled'), key: 'is_global_enabled', sortable: false, align: 'end' as const },
  { title: t('plugins.version'), key: 'version' },
])

function typeColor(type: string) {
  const map: Record<string, string> = {
    normal: 'primary',
    admin: 'warning',
    superuser: 'error',
    hidden: 'grey',
  }
  return map[type] || 'default'
}

function sourceColor(source: string) {
  const map: Record<string, string> = {
    framework: 'error',
    official: 'primary',
    custom: 'success',
    builtin: 'secondary',
    external: 'warning',
  }
  return map[source] || 'default'
}

function sourceLabel(source: string) {
  const map: Record<string, string> = {
    framework: t('plugins.framework'),
    official: t('plugins.official'),
    custom: t('plugins.custom'),
    builtin: t('plugins.builtin'),
    external: t('plugins.external'),
  }
  return map[source] || source
}

async function loadPlugins() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await getPlugins()
    plugins.value = res.data
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('plugins.loadFailed')
  } finally {
    loading.value = false
  }
}

async function togglePlugin(item: PluginRow, nextValue: boolean | null) {
  if (item.is_protected) {
    noticeStore.show(item.protected_reason || t('plugins.cannotDisable'), 'warning')
    return
  }
  const enabled = Boolean(nextValue)
  const previous = item.is_global_enabled
  item.is_global_enabled = enabled
  pendingModule.value = item.module_name
  errorMessage.value = ''
  try {
    await updatePlugin(item.module_name, enabled)
    noticeStore.show(
      t('plugins.toggled', {
        name: item.name || item.module_name,
        action: enabled ? t('plugins.enabledAction') : t('plugins.disabledAction'),
      }),
      'success',
    )
  } catch (error) {
    item.is_global_enabled = previous
    errorMessage.value = error instanceof Error ? error.message : t('plugins.updateFailed')
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    pendingModule.value = ''
  }
}

onMounted(() => {
  void loadPlugins()
})
</script>

<style scoped>
.plugin-enabled-cell {
  min-width: 152px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-left: auto;
}
</style>
