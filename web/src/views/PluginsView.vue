<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('plugins.title') }}</h1>
      <div class="page-actions">
        <v-btn variant="tonal" :loading="loading" @click="loadPlugins">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <v-card class="page-panel">
      <v-tabs v-model="sectionTab" color="primary">
        <v-tab value="core">{{ t('plugins.coreTab') }}</v-tab>
        <v-tab value="plugins">{{ t('plugins.pluginsTab') }}</v-tab>
        <v-tab value="adapters">{{ t('plugins.adaptersTab') }}</v-tab>
        <v-tab value="drivers">{{ t('plugins.driversTab') }}</v-tab>
      </v-tabs>

      <v-divider />

      <v-window v-model="sectionTab">
        <v-window-item value="core">
          <v-card-text class="d-flex flex-column ga-3">
            <div class="settings-shell">
              <div class="settings-shell__toolbar">
                <div class="settings-shell__headline">
                  <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.coreTab') }}</div>
                </div>
                <div class="settings-shell__actions">
                  <v-btn-toggle
                    v-model="coreEditorMode"
                    mandatory
                    density="comfortable"
                    variant="outlined"
                    divided
                    color="primary"
                    class="mode-switch"
                  >
                    <v-btn value="basic">{{ t('plugins.settingsBasicTab') }}</v-btn>
                    <v-btn value="advanced">{{ t('plugins.settingsAdvancedTab') }}</v-btn>
                  </v-btn-toggle>
                  <v-btn
                    v-if="coreEditorMode === 'basic'"
                    color="primary"
                    :loading="coreSaving"
                    :disabled="!hasPendingCoreChanges"
                    @click="saveCoreSettings"
                  >
                    {{ t('plugins.settingsSave') }}
                  </v-btn>
                </div>
              </div>

              <template v-if="coreEditorMode === 'basic'">
                <v-alert v-if="coreErrorMessage" type="error" variant="tonal" density="comfortable">
                  {{ coreErrorMessage }}
                </v-alert>

                <v-progress-linear v-if="coreLoading" indeterminate color="primary" />

                <div v-else class="settings-list-panel">
                  <div
                    v-for="field in coreFields"
                    :key="field.key"
                    class="settings-list-row"
                  >
                    <div class="settings-list-row__main">
                      <div class="settings-list-row__info">
                        <div class="settings-list-row__title">
                          <span class="font-weight-medium">{{ field.key }}</span>
                          <v-chip
                            size="x-small"
                            variant="tonal"
                            :color="field.has_local_override ? 'primary' : 'default'"
                          >
                            {{ field.has_local_override ? t('plugins.settingsLocalShort') : settingsValueSourceLabel(field.value_source) }}
                          </v-chip>
                        </div>
                        <div v-if="field.help" class="settings-list-row__help text-caption text-medium-emphasis">
                          {{ field.help }}
                        </div>
                      </div>

                      <div class="settings-list-row__side">
                        <div class="settings-list-row__value">
                          {{ displayFieldValue(field.current_value) }}
                        </div>
                        <div class="settings-list-row__actions">
                          <v-btn
                            v-if="!coreEditor.isFieldEditing(field) && field.editable"
                            variant="text"
                            size="small"
                            color="primary"
                            @click="coreEditor.startOverride(field)"
                          >
                            {{ t('plugins.settingsAddOverride') }}
                          </v-btn>
                          <v-btn
                            v-if="field.has_local_override"
                            variant="text"
                            size="small"
                            color="warning"
                            :loading="coreClearingKey === field.key"
                            @click="clearCoreField(field)"
                          >
                            {{ t('plugins.settingsClear') }}
                          </v-btn>
                        </div>
                      </div>
                    </div>

                    <div v-if="coreEditor.isFieldEditing(field)" class="settings-list-row__editor">
                      <SettingsFieldEditor
                        v-model="coreForm[field.key]"
                        :field="field"
                        :editing="coreEditor.isFieldEditing(field)"
                        :array-hint="t('plugins.settingsArrayHint')"
                        :json-hint="t('plugins.settingsJsonHint')"
                        :show-readonly="false"
                      />
                    </div>

                    <div
                      v-if="field.has_local_override"
                      class="settings-list-row__footer text-caption text-medium-emphasis"
                    >
                      {{ t('plugins.settingsLocal') }}: {{ displayFieldValue(field.local_value) }}
                    </div>
                  </div>
                </div>
              </template>

              <template v-else>
                <RawSettingsEditor
                  v-model="coreRawText"
                  :description="t('plugins.settingsAdvancedDescription')"
                  :dirty="hasPendingCoreRawChanges"
                  :error-message="coreRawErrorMessage"
                  :loading="coreRawLoading"
                  :reload-label="t('common.refresh')"
                  :save-label="t('plugins.settingsSave')"
                  :saving="coreRawSaving"
                  @reload="loadCoreRawSettings"
                  @save="saveCoreRawSettings"
                />
              </template>
            </div>
          </v-card-text>
        </v-window-item>

        <v-window-item value="plugins">
          <v-card-text class="d-flex flex-column ga-5">
            <div class="page-summary-grid">
              <v-sheet class="summary-card" rounded="lg">
                <div class="summary-card__label">{{ t('plugins.coreProtectedCount') }}</div>
                <div class="summary-card__value">{{ systemPlugins.length }}</div>
              </v-sheet>
              <v-sheet class="summary-card" rounded="lg">
                <div class="summary-card__label">{{ t('plugins.userManagedCount') }}</div>
                <div class="summary-card__value">{{ nonSystemPlugins.length }}</div>
              </v-sheet>
            </div>

            <div class="section-heading">
              <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.configTitle') }}</div>
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
              density="compact"
              class="page-table plugins-table"
            >
              <template #item.name="{ item }">
                <div class="plugins-table__name">
                  <span class="font-weight-medium">{{ item.name || item.module_name }}</span>
                  <span class="text-caption text-medium-emphasis">{{ item.module_name }}</span>
                </div>
              </template>
              <template #item.source="{ value }">
                <v-chip size="small" variant="tonal" :color="sourceColor(value)">
                  {{ sourceLabel(value) }}
                </v-chip>
              </template>
              <template #item.is_global_enabled="{ item }">
                <div class="plugin-enabled-cell">
                  <v-btn
                    size="small"
                    variant="text"
                    color="primary"
                    :loading="settingsLoadingModule === item.module_name"
                    @click="openSettings(item)"
                  >
                    {{ t('plugins.settings') }}
                  </v-btn>
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

            <div class="settings-shell">
              <div class="settings-shell__toolbar">
                <div class="settings-shell__headline">
                  <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.advancedConfigTitle') }}</div>
                </div>
              </div>

              <div class="settings-list-panel">
                <section class="settings-list-row">
                  <div class="plugin-config-section__header">
                    <div class="plugin-config-section__title">{{ t('plugins.moduleSectionTitle') }}</div>
                  </div>
                  <div class="plugin-config-section__toolbar">
                    <v-text-field
                      v-model.trim="newModule"
                      :label="t('plugins.moduleInput')"
                      density="comfortable"
                      hide-details
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
                </section>

                <section class="settings-list-row">
                  <div class="plugin-config-section__header">
                    <div class="plugin-config-section__title">{{ t('plugins.dirSectionTitle') }}</div>
                  </div>
                  <div class="plugin-config-section__toolbar">
                    <v-text-field
                      v-model.trim="newDir"
                      :label="t('plugins.dirInput')"
                      density="comfortable"
                      hide-details
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
                </section>
              </div>
            </div>
          </v-card-text>
        </v-window-item>

        <v-window-item value="adapters">
          <v-card-text class="d-flex flex-column ga-5">
            <div class="d-flex justify-space-between align-center flex-wrap ga-3">
              <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.adaptersTab') }}</div>
              <v-sheet class="summary-card" rounded="lg">
                <div class="summary-card__label">{{ t('plugins.adapterCount') }}</div>
                <div class="summary-card__value">{{ adapterModules.length }}</div>
              </v-sheet>
            </div>
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
              <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.driversTab') }}</div>
              <v-sheet class="summary-card" rounded="lg">
                <div class="summary-card__label">{{ t('plugins.driverCount') }}</div>
                <div class="summary-card__value">{{ driverBuiltin.length }}</div>
              </v-sheet>
            </div>
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

    <v-dialog v-model="settingsDialogVisible" max-width="840">
      <v-card>
        <v-card-title class="d-flex flex-column align-start ga-1">
          <span>{{ t('plugins.settingsTitle', { name: settingsPlugin?.name || settingsPlugin?.module_name || '' }) }}</span>
          <span class="text-caption text-medium-emphasis">
            {{ settingsPlugin?.module_name }}
          </span>
        </v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <div v-if="settingsState" class="d-flex flex-wrap ga-2">
            <v-chip size="small" variant="tonal" color="primary">
              {{ settingsState.section }}
            </v-chip>
            <v-chip size="small" variant="tonal" :color="settingsState.legacy_flatten ? 'warning' : 'default'">
              {{ settingsState.legacy_flatten ? t('plugins.settingsLegacy') : settingsSourceLabel(settingsState.config_source) }}
            </v-chip>
          </div>

          <v-alert v-if="settingsErrorMessage" type="error" variant="tonal" density="comfortable">
            {{ settingsErrorMessage }}
          </v-alert>

          <v-progress-linear v-if="settingsDialogLoading" indeterminate color="primary" />

          <div v-if="!settingsDialogLoading" class="settings-shell">
            <div class="settings-shell__toolbar settings-shell__toolbar--dialog">
              <div class="settings-shell__headline" />
              <div class="settings-shell__actions">
                <v-btn-toggle
                  v-model="settingsEditorMode"
                  mandatory
                  density="comfortable"
                  variant="outlined"
                  divided
                  color="primary"
                  class="mode-switch"
                >
                  <v-btn value="basic">{{ t('plugins.settingsBasicTab') }}</v-btn>
                  <v-btn value="advanced">{{ t('plugins.settingsAdvancedTab') }}</v-btn>
                </v-btn-toggle>
                <v-btn
                  v-if="settingsEditorMode === 'basic'"
                  color="primary"
                  :disabled="!settingsState?.has_config_model || !hasPendingPluginChanges"
                  :loading="settingsSaving"
                  @click="saveSettings"
                >
                  {{ t('plugins.settingsSave') }}
                </v-btn>
              </div>
            </div>

            <template v-if="settingsEditorMode === 'basic'">
              <div v-if="!settingsState?.has_config_model || settingsFields.length === 0" class="text-body-2 text-medium-emphasis">
                {{ t('plugins.settingsEmpty') }}
              </div>

              <div v-else class="settings-list-panel">
                <div
                  v-for="field in settingsFields"
                  :key="field.key"
                  class="settings-list-row"
                >
                  <div class="settings-list-row__main">
                    <div>
                      <div class="font-weight-medium">{{ field.key }}</div>
                      <div v-if="field.help" class="text-caption text-medium-emphasis">
                        {{ field.help }}
                      </div>
                    </div>
                    <div class="settings-list-row__chips">
                      <v-chip size="x-small" variant="tonal">{{ field.type }}</v-chip>
                      <v-chip size="x-small" variant="tonal" color="secondary">{{ field.editor }}</v-chip>
                      <v-chip size="x-small" variant="tonal" :color="field.editable ? 'default' : 'warning'">
                        {{ settingsValueSourceLabel(field.value_source) }}
                      </v-chip>
                      <v-chip v-if="field.choices.length > 0" size="x-small" variant="tonal" color="secondary">
                        {{ field.choices.join(', ') }}
                      </v-chip>
                    </div>
                  </div>

                  <div class="settings-list-row__actions">
                    <v-btn
                      v-if="!pluginEditor.isFieldEditing(field) && field.editable"
                      variant="text"
                      size="small"
                      color="primary"
                      @click="pluginEditor.startOverride(field)"
                    >
                      {{ t('plugins.settingsAddOverride') }}
                    </v-btn>
                    <v-btn
                      v-if="field.has_local_override"
                      variant="text"
                      size="small"
                      color="warning"
                      :loading="settingsClearingKey === field.key"
                      @click="clearPluginField(field)"
                    >
                      {{ t('plugins.settingsClear') }}
                    </v-btn>
                  </div>

                  <SettingsFieldEditor
                    v-model="settingsForm[field.key]"
                    :field="field"
                    :editing="pluginEditor.isFieldEditing(field)"
                    :array-hint="t('plugins.settingsArrayHint')"
                    :json-hint="t('plugins.settingsJsonHint')"
                    />

                  <div class="settings-list-row__meta text-caption text-medium-emphasis">
                    <span>{{ t('plugins.settingsCurrent') }}: {{ displayFieldValue(field.current_value) }}</span>
                    <span v-if="field.has_local_override">{{ t('plugins.settingsLocal') }}: {{ displayFieldValue(field.local_value) }}</span>
                    <span v-if="field.global_key">{{ field.global_key }}</span>
                  </div>
                </div>
              </div>
            </template>

            <template v-else>
              <RawSettingsEditor
                v-model="settingsRawText"
                :description="t('plugins.settingsAdvancedDescription')"
                :dirty="hasPendingPluginRawChanges"
                :error-message="settingsRawErrorMessage"
                :loading="settingsRawLoading"
                :reload-label="t('common.refresh')"
                :save-label="t('plugins.settingsSave')"
                :saving="settingsRawSaving"
                @reload="settingsPlugin && loadPluginRawSettings(settingsPlugin.module_name)"
                @save="savePluginRawSettings"
              />
            </template>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="settingsDialogVisible = false">{{ t('common.cancel') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getCoreSettings,
  getCoreSettingsRaw,
  getAdapterConfig,
  getDriverConfig,
  getPluginConfig,
  getPluginSettings,
  getPluginSettingsRaw,
  getPlugins,
  updateCoreSettings,
  updateCoreSettingsRaw,
  updatePlugin,
  updatePluginConfig,
  updatePluginSettings,
  updatePluginSettingsRaw,
  type ModuleConfigItem,
  type DirConfigItem,
  type DriverConfigItem,
  type RawSettingsResponse,
} from '@/api'
import { getErrorMessage } from '@/api/client'
import { useNoticeStore } from '@/stores/notice'
import {
  displayFieldValue,
  type PluginSettingField,
  type PluginSettingsState,
} from '@/views/plugins/settingsEditor'
import RawSettingsEditor from '@/views/plugins/RawSettingsEditor.vue'
import SettingsFieldEditor from '@/views/plugins/SettingsFieldEditor.vue'
import { useSettingsEditor } from '@/views/plugins/useSettingsEditor'

interface PluginRow {
  module_name: string
  name: string | null
  description: string | null
  source: string
  is_global_enabled: boolean
  is_protected: boolean
  protected_reason: string | null
}

const plugins = ref<PluginRow[]>([])
const loading = ref(false)
const pendingModule = ref('')
const errorMessage = ref('')
const sectionTab = ref('plugins')
const hideSystemPlugins = ref(true)
const configSaving = ref(false)
const adapterModules = ref<ModuleConfigItem[]>([])
const driverBuiltin = ref<DriverConfigItem[]>([])
const pluginModules = ref<ModuleConfigItem[]>([])
const pluginDirs = ref<DirConfigItem[]>([])
const newModule = ref('')
const newDir = ref('')
const coreEditorMode = ref<'basic' | 'advanced'>('basic')
const coreRawText = ref('')
const coreRawInitialText = ref('')
const coreRawLoading = ref(false)
const coreRawSaving = ref(false)
const coreRawErrorMessage = ref('')
const settingsDialogVisible = ref(false)
const settingsLoadingModule = ref('')
const settingsPlugin = ref<PluginRow | null>(null)
const settingsEditorMode = ref<'basic' | 'advanced'>('basic')
const settingsRawText = ref('')
const settingsRawInitialText = ref('')
const settingsRawLoading = ref(false)
const settingsRawSaving = ref(false)
const settingsRawErrorMessage = ref('')
const noticeStore = useNoticeStore()
const { t } = useI18n()

const coreEditor = useSettingsEditor({
  load: getCoreSettings,
  save: (values) => updateCoreSettings({ values }),
  clear: (key) => updateCoreSettings({ values: {}, clear: [key] }),
  messages: {
    clearSuccess: t('plugins.settingsCleared'),
    invalidJson: t('plugins.settingsInvalidJson'),
    loadFailed: t('plugins.settingsLoadFailed'),
    saveFailed: t('plugins.settingsSaveFailed'),
    saveSuccess: t('plugins.settingsSaved'),
  },
})

const pluginEditor = useSettingsEditor({
  save: (values) => updatePluginSettings(settingsPlugin.value!.module_name, { values }),
  clear: (key) => updatePluginSettings(settingsPlugin.value!.module_name, { values: {}, clear: [key] }),
  messages: {
    clearSuccess: t('plugins.settingsCleared'),
    invalidJson: t('plugins.settingsInvalidJson'),
    loadFailed: t('plugins.settingsLoadFailed'),
    saveFailed: t('plugins.settingsSaveFailed'),
    saveSuccess: t('plugins.settingsSaved'),
  },
})

const settingsDialogLoading = pluginEditor.loading
const settingsSaving = pluginEditor.saving
const settingsClearingKey = pluginEditor.clearingKey
const settingsErrorMessage = pluginEditor.errorMessage
const settingsState = pluginEditor.state
const settingsForm = pluginEditor.form
const coreLoading = coreEditor.loading
const coreSaving = coreEditor.saving
const coreClearingKey = coreEditor.clearingKey
const coreErrorMessage = coreEditor.errorMessage
const coreSettings = coreEditor.state
const coreForm = coreEditor.form
const hasPendingCoreRawChanges = computed(() => coreRawText.value !== coreRawInitialText.value)
const hasPendingPluginRawChanges = computed(() => settingsRawText.value !== settingsRawInitialText.value)

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

const settingsFields = pluginEditor.fields
const coreFields = coreEditor.fields

const systemPlugins = computed(() =>
  plugins.value.filter((item) => item.source === 'framework'),
)

const nonSystemPlugins = computed(() =>
  plugins.value.filter((item) => !systemPlugins.value.some((systemItem) => systemItem.module_name === item.module_name)),
)

const visiblePlugins = computed(() =>
  hideSystemPlugins.value ? nonSystemPlugins.value : plugins.value,
)

const SOURCE_COLORS: Record<string, string> = {
  framework: 'error',
  official: 'primary',
  custom: 'success',
  builtin: 'secondary',
  external: 'warning',
}

function sourceColor(source: string) {
  return SOURCE_COLORS[source] || 'default'
}

function labelFromMap(source: string, map: Record<string, string>) {
  return map[source] || source
}

function sourceLabel(source: string) {
  return labelFromMap(source, {
    framework: t('plugins.framework'),
    official: t('plugins.official'),
    custom: t('plugins.custom'),
    builtin: t('plugins.builtin'),
    external: t('plugins.external'),
  })
}

function settingsSourceLabel(source: string) {
  return labelFromMap(source, {
    static_scan: t('plugins.settingsSourceStaticScan'),
    plugin_metadata: t('plugins.settingsSourceMetadata'),
    none: t('plugins.settingsSourceNone'),
    manual: t('plugins.settingsSourceManual'),
    built_in: t('plugins.settingsSourceBuiltIn'),
  })
}

function settingsValueSourceLabel(source: string) {
  return labelFromMap(source, {
    default: t('plugins.settingsValueSourceDefault'),
    plugin_section: t('plugins.settingsValueSourcePlugin'),
    legacy_global: t('plugins.settingsValueSourceLegacy'),
    env: t('plugins.settingsValueSourceEnv'),
  })
}

const hasPendingCoreChanges = coreEditor.hasPendingChanges
const hasPendingPluginChanges = pluginEditor.hasPendingChanges

function applyCoreRawState(nextState: RawSettingsResponse) {
  coreRawText.value = nextState.text
  coreRawInitialText.value = nextState.text
}

function applyPluginRawState(nextState: RawSettingsResponse) {
  settingsRawText.value = nextState.text
  settingsRawInitialText.value = nextState.text
}

async function loadCoreRawSettings() {
  coreRawLoading.value = true
  coreRawErrorMessage.value = ''
  try {
    const response = await getCoreSettingsRaw()
    applyCoreRawState(response.data)
  } catch (error) {
    coreRawErrorMessage.value = getErrorMessage(error, t('plugins.settingsRawLoadFailed'))
  } finally {
    coreRawLoading.value = false
  }
}

async function loadPluginRawSettings(moduleName: string) {
  settingsRawLoading.value = true
  settingsRawErrorMessage.value = ''
  try {
    const response = await getPluginSettingsRaw(moduleName)
    applyPluginRawState(response.data)
  } catch (error) {
    settingsRawErrorMessage.value = getErrorMessage(error, t('plugins.settingsRawLoadFailed'))
  } finally {
    settingsRawLoading.value = false
  }
}

async function loadPlugins() {
  loading.value = true
  coreLoading.value = true
  coreRawLoading.value = true
  errorMessage.value = ''
  coreErrorMessage.value = ''
  coreRawErrorMessage.value = ''
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
    errorMessage.value = getErrorMessage(error, t('plugins.loadFailed'))
  } finally {
    loading.value = false
  }

  try {
    const coreResponse = await getCoreSettings()
    coreEditor.applyState(coreResponse.data)
    coreErrorMessage.value = ''
  } catch (error) {
    coreErrorMessage.value = getErrorMessage(error, t('plugins.settingsLoadFailed'))
  } finally {
    coreLoading.value = false
  }

  await loadCoreRawSettings()
}

async function openSettings(item: PluginRow) {
  settingsPlugin.value = item
  settingsDialogVisible.value = true
  settingsEditorMode.value = 'basic'
  settingsDialogLoading.value = true
  settingsLoadingModule.value = item.module_name
  pluginEditor.reset()
  settingsRawText.value = ''
  settingsRawInitialText.value = ''
  settingsRawErrorMessage.value = ''
  try {
    const settingsResponse = await getPluginSettings(item.module_name)
    pluginEditor.applyState(settingsResponse.data)
  } catch (error) {
    settingsErrorMessage.value = getErrorMessage(error, t('plugins.settingsLoadFailed'))
  } finally {
    settingsDialogLoading.value = false
    settingsLoadingModule.value = ''
  }
  await loadPluginRawSettings(item.module_name)
}

async function saveSettings() {
  if (!settingsPlugin.value || !settingsState.value) return
  await pluginEditor.submit()
}

async function clearPluginField(field: PluginSettingField) {
  if (!settingsPlugin.value) return
  await pluginEditor.clearField(field)
}

async function saveCoreSettings() {
  if (!coreSettings.value) return
  await coreEditor.submit()
}

async function saveCoreRawSettings() {
  if (!hasPendingCoreRawChanges.value) return
  coreRawSaving.value = true
  coreRawErrorMessage.value = ''
  try {
    const rawResponse = await updateCoreSettingsRaw({ text: coreRawText.value })
    const settingsResponse = await getCoreSettings()
    applyCoreRawState(rawResponse.data)
    coreEditor.applyState(settingsResponse.data)
    noticeStore.show(t('plugins.settingsRawSaved'), 'success')
  } catch (error) {
    const message = getErrorMessage(error, t('plugins.settingsRawSaveFailed'))
    coreRawErrorMessage.value = message
    noticeStore.show(message, 'error')
  } finally {
    coreRawSaving.value = false
  }
}

async function clearCoreField(field: PluginSettingField) {
  await coreEditor.clearField(field)
}

async function savePluginRawSettings() {
  if (!settingsPlugin.value || !hasPendingPluginRawChanges.value) return
  settingsRawSaving.value = true
  settingsRawErrorMessage.value = ''
  try {
    const rawResponse = await updatePluginSettingsRaw(settingsPlugin.value.module_name, {
      text: settingsRawText.value,
    })
    const settingsResponse = await getPluginSettings(settingsPlugin.value.module_name)
    applyPluginRawState(rawResponse.data)
    pluginEditor.applyState(settingsResponse.data)
    noticeStore.show(t('plugins.settingsRawSaved'), 'success')
  } catch (error) {
    const message = getErrorMessage(error, t('plugins.settingsRawSaveFailed'))
    settingsRawErrorMessage.value = message
    noticeStore.show(message, 'error')
  } finally {
    settingsRawSaving.value = false
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
    errorMessage.value = getErrorMessage(error, t('plugins.configSaveFailed'))
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

function moduleChipColor(item: ModuleConfigItem) {
  if (item.is_loaded) return 'success'
  if (item.is_importable) return 'warning'
  return 'error'
}

function dirChipColor(item: DirConfigItem) {
  if (!item.exists) return 'error'
  if (item.is_loaded) return 'success'
  return 'warning'
}

function moduleStatusText(item: ModuleConfigItem) {
  if (item.is_loaded) return t('plugins.moduleLoaded')
  if (item.is_importable) return t('plugins.moduleRegisteredOnly')
  return t('plugins.moduleMissing')
}

function dirStatusText(item: DirConfigItem) {
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
    errorMessage.value = getErrorMessage(error, t('plugins.updateFailed'))
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
.settings-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-shell__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.settings-shell__toolbar--dialog {
  padding-bottom: 4px;
}

.settings-shell__headline {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.settings-shell__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.mode-switch {
  border-radius: 999px;
}

.settings-list-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 14px;
}

.settings-list-row {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.settings-list-row:last-child {
  border-bottom: 0;
}

.settings-list-row__main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 360px);
  gap: 16px;
  align-items: center;
}

.settings-list-row__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.settings-list-row__title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.settings-list-row__help {
  line-height: 1.35;
}

.settings-list-row__side {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.settings-list-row__value {
  min-height: 44px;
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(var(--v-theme-on-surface), 0.02);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.86rem;
  line-height: 1.35;
  word-break: break-word;
}

.settings-list-row__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: wrap;
}

.settings-list-row__editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.settings-list-row__footer {
  display: flex;
  align-items: center;
  gap: 6px;
}

.plugin-enabled-cell {
  min-width: 152px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-left: auto;
}

.config-input {
  flex: 1 1 300px;
  min-width: 220px;
}

.config-chip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 32px;
}

.plugin-config-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.plugin-config-section__title {
  font-size: 0.84rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.plugin-config-section__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.plugins-table__name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}

.settings-list-row__chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.settings-list-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

:deep(.plugins-table .v-selection-control) {
  justify-content: flex-end;
}

:deep(.plugins-table .v-selection-control__wrapper) {
  transform: scale(0.92);
  transform-origin: center;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@media (max-width: 960px) {
  .settings-shell__toolbar {
    align-items: flex-start;
  }

  .settings-shell__actions {
    width: 100%;
    justify-content: space-between;
  }

  .settings-list-row__main {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .settings-list-row__side {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .settings-list-row__chips {
    justify-content: flex-start;
  }
}
</style>
