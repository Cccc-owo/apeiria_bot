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
      <v-tabs v-model="sectionTab" color="primary">
        <v-tab value="plugins">{{ t('plugins.pluginsTab') }}</v-tab>
        <v-tab value="adapters">{{ t('plugins.adaptersTab') }}</v-tab>
        <v-tab value="drivers">{{ t('plugins.driversTab') }}</v-tab>
      </v-tabs>

      <v-divider />

      <v-window v-model="sectionTab">
        <v-window-item value="plugins">
          <v-card-text class="d-flex flex-column ga-5">
            <div class="d-flex flex-wrap ga-3">
              <v-sheet class="summary-card" rounded="lg" border>
                <div class="text-caption text-medium-emphasis">{{ t('plugins.coreProtectedCount') }}</div>
                <div class="text-h5 font-weight-bold">{{ corePlugins.filter((item) => item.is_protected).length }}</div>
              </v-sheet>
              <v-sheet class="summary-card" rounded="lg" border>
                <div class="text-caption text-medium-emphasis">{{ t('plugins.userManagedCount') }}</div>
                <div class="text-h5 font-weight-bold">{{ userPlugins.length }}</div>
              </v-sheet>
            </div>

            <div class="d-flex justify-space-between align-center flex-wrap ga-3">
              <div class="d-flex flex-column ga-1">
                <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.configTitle') }}</div>
                <div class="text-body-2 text-medium-emphasis">
                  {{ t('plugins.configDescription') }}
                </div>
              </div>
              <v-switch
                v-model="hideSystemPlugins"
                color="primary"
                hide-details
                inset
                :label="t('plugins.hideSystemDependencies')"
              />
            </div>

            <v-data-table
              :headers="pluginHeaders"
              :items="visiblePlugins"
              :loading="loading"
              density="comfortable"
            >
              <template #item.name="{ item }">
                <div class="d-flex flex-column py-2">
                  <span class="font-weight-medium">{{ item.name || item.module_name }}</span>
                  <span class="text-caption text-medium-emphasis">{{ item.module_name }}</span>
                </div>
              </template>
              <template #item.source="{ value }">
                <v-chip size="small" variant="outlined" :color="sourceColor(value)">
                  {{ sourceLabel(value) }}
                </v-chip>
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
              <template #no-data>
                <div class="py-6 text-body-2 text-medium-emphasis text-center">
                  {{ t('plugins.noVisiblePlugins') }}
                </div>
              </template>
            </v-data-table>

            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  {{ t('plugins.advancedConfigTitle') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <div class="d-flex flex-column ga-5">
                    <div class="d-flex flex-column ga-3">
                      <div class="d-flex flex-column ga-1">
                        <div class="text-subtitle-2 font-weight-medium">{{ t('plugins.moduleSectionTitle') }}</div>
                        <div class="text-body-2 text-medium-emphasis">
                          {{ t('plugins.directConfigDescription') }}
                        </div>
                      </div>
                      <div class="d-flex flex-wrap ga-2 align-center">
                        <v-text-field
                          v-model.trim="newModule"
                          :label="t('plugins.moduleInput')"
                          density="comfortable"
                          hide-details
                          variant="outlined"
                          class="config-input"
                          @keydown.enter.prevent="addModule"
                        />
                        <v-btn
                          color="primary"
                          variant="tonal"
                          :loading="configSaving"
                          @click="addModule"
                        >
                          {{ t('plugins.addModule') }}
                        </v-btn>
                      </div>
                      <div class="config-chip-row">
                        <v-chip
                          v-for="moduleItem in pluginModules"
                          :key="moduleItem.name"
                          closable
                          variant="tonal"
                          :color="moduleChipColor(moduleItem)"
                          @click:close="removeModule(moduleItem.name)"
                        >
                          {{ moduleItem.name }}
                          <v-tooltip activator="parent" location="top">
                            {{ moduleStatusText(moduleItem) }}
                          </v-tooltip>
                        </v-chip>
                        <span v-if="pluginModules.length === 0" class="text-body-2 text-medium-emphasis">
                          {{ t('plugins.emptyModules') }}
                        </span>
                      </div>
                    </div>

                    <div class="d-flex flex-column ga-3">
                      <div class="d-flex flex-column ga-1">
                        <div class="text-subtitle-2 font-weight-medium">{{ t('plugins.dirSectionTitle') }}</div>
                        <div class="text-body-2 text-medium-emphasis">
                          {{ t('plugins.configDirDescription') }}
                        </div>
                      </div>
                      <div class="d-flex flex-wrap ga-2 align-center">
                        <v-text-field
                          v-model.trim="newDir"
                          :label="t('plugins.dirInput')"
                          density="comfortable"
                          hide-details
                          variant="outlined"
                          class="config-input"
                          @keydown.enter.prevent="addDir"
                        />
                        <v-btn
                          color="secondary"
                          variant="tonal"
                          :loading="configSaving"
                          @click="addDir"
                        >
                          {{ t('plugins.addDir') }}
                        </v-btn>
                      </div>
                      <div class="config-chip-row">
                        <v-chip
                          v-for="dirItem in pluginDirs"
                          :key="dirItem.path"
                          closable
                          variant="tonal"
                          :color="dirChipColor(dirItem)"
                          @click:close="removeDir(dirItem.path)"
                        >
                          {{ dirItem.path }}
                          <v-tooltip activator="parent" location="top">
                            {{ dirStatusText(dirItem) }}
                          </v-tooltip>
                        </v-chip>
                        <span v-if="pluginDirs.length === 0" class="text-body-2 text-medium-emphasis">
                          {{ t('plugins.emptyDirs') }}
                        </span>
                      </div>
                    </div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-window-item>

        <v-window-item value="adapters">
          <v-card-text class="d-flex flex-column ga-5">
            <div class="d-flex justify-space-between align-center flex-wrap ga-3">
              <div class="d-flex flex-column ga-1">
                <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.adaptersTab') }}</div>
                <div class="text-body-2 text-medium-emphasis">
                  {{ t('plugins.runtimeReadonlySummary') }}
                </div>
              </div>
              <v-sheet class="summary-card" rounded="lg" border>
                <div class="text-caption text-medium-emphasis">{{ t('plugins.adapterCount') }}</div>
                <div class="text-h5 font-weight-bold">{{ adapterModules.length }}</div>
              </v-sheet>
            </div>

            <v-alert type="info" variant="tonal" density="comfortable">
              {{ t('plugins.adapterReadonlyDescription') }}
            </v-alert>
            <div class="config-chip-row">
              <v-chip
                v-for="adapterItem in adapterModules"
                :key="adapterItem.name"
                variant="tonal"
                :color="moduleChipColor(adapterItem)"
              >
                {{ adapterItem.name }}
                <v-tooltip activator="parent" location="top">
                  {{ moduleStatusText(adapterItem) }}
                </v-tooltip>
              </v-chip>
              <span v-if="adapterModules.length === 0" class="text-body-2 text-medium-emphasis">
                {{ t('plugins.emptyAdapterModules') }}
              </span>
            </div>
          </v-card-text>
        </v-window-item>

        <v-window-item value="drivers">
          <v-card-text class="d-flex flex-column ga-5">
            <div class="d-flex justify-space-between align-center flex-wrap ga-3">
              <div class="d-flex flex-column ga-1">
                <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.driversTab') }}</div>
                <div class="text-body-2 text-medium-emphasis">
                  {{ t('plugins.runtimeReadonlySummary') }}
                </div>
              </div>
              <v-sheet class="summary-card" rounded="lg" border>
                <div class="text-caption text-medium-emphasis">{{ t('plugins.driverCount') }}</div>
                <div class="text-h5 font-weight-bold">{{ driverBuiltin.length }}</div>
              </v-sheet>
            </div>

            <v-alert type="info" variant="tonal" density="comfortable">
              {{ t('plugins.driverReadonlyDescription') }}
            </v-alert>
            <div class="config-chip-row">
              <v-chip
                v-for="driverItem in driverBuiltin"
                :key="driverItem.name"
                variant="tonal"
                :color="driverChipColor(driverItem)"
              >
                {{ driverItem.name }}
                <v-tooltip activator="parent" location="top">
                  {{ driverStatusText(driverItem) }}
                </v-tooltip>
              </v-chip>
              <span v-if="driverBuiltin.length === 0" class="text-body-2 text-medium-emphasis">
                {{ t('plugins.emptyDriverBuiltin') }}
              </span>
            </div>
          </v-card-text>
        </v-window-item>
      </v-window>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getAdapterConfig,
  getDriverConfig,
  getPluginConfig,
  getPlugins,
  updatePlugin,
  updatePluginConfig,
} from '@/api'
import { useNoticeStore } from '@/stores/notice'

interface PluginRow {
  module_name: string
  name: string | null
  description: string | null
  source: string
  is_global_enabled: boolean
  is_protected: boolean
  protected_reason: string | null
}

interface PluginConfigModuleItem {
  name: string
  is_loaded: boolean
  is_importable: boolean
}

interface PluginConfigDirItem {
  path: string
  exists: boolean
  is_loaded: boolean
}

interface DriverConfigItem {
  name: string
  is_active: boolean
}

const plugins = ref<PluginRow[]>([])
const loading = ref(false)
const pendingModule = ref('')
const errorMessage = ref('')
const sectionTab = ref('plugins')
const hideSystemPlugins = ref(true)
const configSaving = ref(false)
const adapterModules = ref<PluginConfigModuleItem[]>([])
const driverBuiltin = ref<DriverConfigItem[]>([])
const pluginModules = ref<PluginConfigModuleItem[]>([])
const pluginDirs = ref<PluginConfigDirItem[]>([])
const newModule = ref('')
const newDir = ref('')
const noticeStore = useNoticeStore()
const { t } = useI18n()

function normalizeConfigEntry(value: string) {
  const normalized = value.trim()
  if (!normalized) return ''
  if (['none', 'null'].includes(normalized.toLowerCase())) return ''
  return normalized
}

function normalizeConfigEntries(values: string[]) {
  return Array.from(new Set(values.map(normalizeConfigEntry).filter(Boolean))).sort()
}

const pluginHeaders = computed(() => [
  { title: t('plugins.name'), key: 'name' },
  { title: t('plugins.source'), key: 'source' },
  { title: t('plugins.enabled'), key: 'is_global_enabled', sortable: false, align: 'end' as const },
])

const corePlugins = computed(() =>
  plugins.value.filter((item) => item.is_protected || ['framework', 'builtin'].includes(item.source)),
)

const userPlugins = computed(() =>
  plugins.value.filter((item) => !corePlugins.value.some((coreItem) => coreItem.module_name === item.module_name)),
)

const visiblePlugins = computed(() =>
  hideSystemPlugins.value ? userPlugins.value : plugins.value,
)

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
    const [pluginsResponse, pluginConfigResponse, adapterConfigResponse, driverConfigResponse] = await Promise.all([
      getPlugins(),
      getPluginConfig(),
      getAdapterConfig(),
      getDriverConfig(),
    ])
    plugins.value = pluginsResponse.data
    pluginModules.value = pluginConfigResponse.data.modules
    pluginDirs.value = pluginConfigResponse.data.dirs
    adapterModules.value = adapterConfigResponse.data.modules
    driverBuiltin.value = driverConfigResponse.data.builtin
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('plugins.loadFailed')
  } finally {
    loading.value = false
  }
}

async function savePluginConfig(modules: string[], dirs: string[]) {
  configSaving.value = true
  errorMessage.value = ''
  try {
    const response = await updatePluginConfig({ modules, dirs })
    pluginModules.value = response.data.modules
    pluginDirs.value = response.data.dirs
    noticeStore.show(t('plugins.configSaved'), 'success')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('plugins.configSaveFailed')
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    configSaving.value = false
  }
}

async function addModule() {
  if (!newModule.value) return
  const nextModules = normalizeConfigEntries([
    ...pluginModules.value.map((item) => item.name),
    newModule.value,
  ])
  newModule.value = ''
  await savePluginConfig(nextModules, normalizeConfigEntries(pluginDirs.value.map((item) => item.path)))
}

async function removeModule(moduleName: string) {
  await savePluginConfig(
    pluginModules.value.filter((item) => item.name !== moduleName).map((item) => item.name),
    normalizeConfigEntries(pluginDirs.value.map((item) => item.path)),
  )
}

async function addDir() {
  if (!newDir.value) return
  const nextDirs = normalizeConfigEntries([
    ...pluginDirs.value.map((item) => item.path),
    newDir.value,
  ])
  newDir.value = ''
  await savePluginConfig(pluginModules.value.map((item) => item.name), nextDirs)
}

async function removeDir(dirName: string) {
  await savePluginConfig(
    pluginModules.value.map((item) => item.name),
    normalizeConfigEntries(
      pluginDirs.value.filter((item) => item.path !== dirName).map((item) => item.path),
    ),
  )
}

function moduleChipColor(item: PluginConfigModuleItem) {
  if (item.is_loaded) return 'success'
  if (item.is_importable) return 'warning'
  return 'error'
}

function dirChipColor(item: PluginConfigDirItem) {
  if (!item.exists) return 'error'
  if (item.is_loaded) return 'success'
  return 'warning'
}

function moduleStatusText(item: PluginConfigModuleItem) {
  if (item.is_loaded) return t('plugins.moduleLoaded')
  if (item.is_importable) return t('plugins.moduleRegisteredOnly')
  return t('plugins.moduleMissing')
}

function dirStatusText(item: PluginConfigDirItem) {
  if (!item.exists) return t('plugins.dirMissing')
  if (item.is_loaded) return t('plugins.dirLoaded')
  return t('plugins.dirRegisteredOnly')
}

function driverChipColor(item: DriverConfigItem) {
  return item.is_active ? 'success' : 'warning'
}

function driverStatusText(item: DriverConfigItem) {
  return item.is_active ? t('plugins.driverActive') : t('plugins.driverRegisteredOnly')
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

.config-input {
  flex: 1 1 320px;
  min-width: 240px;
}

.config-chip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 32px;
}

.summary-card {
  min-width: 180px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
