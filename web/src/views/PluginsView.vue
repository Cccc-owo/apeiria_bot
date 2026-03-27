<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('plugins.title') }}</h1>
      <div class="page-actions">
        <v-btn :loading="loading" variant="tonal" @click="loadPluginManagement">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
      {{ errorMessage }}
    </v-alert>

    <v-card class="page-panel">
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
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('plugins.visibleCount') }}</div>
            <div class="summary-card__value">{{ visiblePlugins.length }}</div>
          </v-sheet>
        </div>

        <div class="section-heading">
          <div class="section-heading__main">
            <div class="text-subtitle-1 font-weight-medium">{{ t('plugins.configTitle') }}</div>
            <v-text-field
              v-model.trim="pluginSearch"
              class="plugin-search"
              density="comfortable"
              hide-details
              :label="t('plugins.search')"
              prepend-inner-icon="mdi-magnify"
            />
          </div>
          <div class="section-heading__actions">
            <v-switch
              v-model="hideSystemPlugins"
              color="primary"
              hide-details
              inset
              :label="t('plugins.hideSystemDependencies')"
            />
          </div>
        </div>

        <v-data-table
          class="page-table plugins-table"
          density="compact"
          :headers="pluginHeaders"
          :items="visiblePlugins"
          :loading="loading"
        >
          <template #item.name="{ item }">
            <div class="plugins-table__name">
              <div class="plugins-table__title-row">
                <span class="font-weight-medium">{{ item.name || item.module_name }}</span>
                <v-chip
                  v-if="item.admin_level > 0"
                  color="secondary"
                  size="x-small"
                  variant="tonal"
                >
                  Lv.{{ item.admin_level }}
                </v-chip>
                <v-chip
                  :color="item.plugin_type === 'admin' || item.plugin_type === 'superuser' ? 'warning' : 'default'"
                  size="x-small"
                  variant="tonal"
                >
                  {{ item.plugin_type }}
                </v-chip>
              </div>
              <span class="text-caption text-medium-emphasis">{{ item.module_name }}</span>
              <span v-if="item.description" class="text-caption text-medium-emphasis plugins-table__description">
                {{ item.description }}
              </span>
              <div v-if="pluginMetaSummary(item)" class="text-caption text-medium-emphasis plugins-table__meta">
                {{ pluginMetaSummary(item) }}
              </div>
              <div v-if="item.required_plugins.length > 0 || item.dependent_plugins.length > 0" class="plugins-table__relations">
                <v-chip
                  v-for="dependency in item.required_plugins"
                  :key="`req:${item.module_name}:${dependency}`"
                  color="info"
                  size="x-small"
                  variant="tonal"
                >
                  {{ t('plugins.requires', { name: dependency }) }}
                </v-chip>
                <v-chip
                  v-for="dependent in item.dependent_plugins"
                  :key="`dep:${item.module_name}:${dependent}`"
                  color="warning"
                  size="x-small"
                  variant="tonal"
                >
                  {{ t('plugins.requiredBy', { name: dependent }) }}
                </v-chip>
              </div>
            </div>
          </template>
          <template #item.source="{ value }">
            <v-chip :color="sourceColor(value)" size="small" variant="tonal">
              {{ sourceLabel(value) }}
            </v-chip>
          </template>
          <template #item.is_global_enabled="{ item }">
            <div class="plugin-status-card">
              <div class="plugin-status-card__toolbar">
                <div class="plugin-status-card__actions">
                  <v-chip
                    v-if="item.is_protected"
                    class="plugin-status-card__protected-chip"
                    color="warning"
                    size="small"
                    :title="item.protected_reason || ''"
                    variant="tonal"
                  >
                    {{ t('plugins.protected') }}
                  </v-chip>
                  <v-btn
                    color="primary"
                    :loading="settingsLoadingModule === item.module_name"
                    size="small"
                    variant="text"
                    @click="openSettings(item)"
                  >
                    {{ t('plugins.settings') }}
                  </v-btn>
                  <v-switch
                    color="success"
                    :disabled="item.is_protected"
                    hide-details
                    inset
                    :loading="pendingModule === item.module_name"
                    :model-value="item.is_global_enabled"
                    @update:model-value="togglePlugin(item, $event)"
                  />
                </div>
              </div>
              <div v-if="pluginRiskLabel(item)" class="plugin-status-card__hint text-caption text-medium-emphasis">
                {{ pluginRiskLabel(item) }}
              </div>
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
                  class="config-input"
                  density="comfortable"
                  hide-details
                  :label="t('plugins.moduleInput')"
                  @keydown.enter.prevent="addModule"
                />
                <v-btn
                  color="primary"
                  :loading="configSaving"
                  variant="tonal"
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
                  :color="moduleChipColor(moduleItem)"
                  variant="tonal"
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
                  class="config-input"
                  density="comfortable"
                  hide-details
                  :label="t('plugins.dirInput')"
                  @keydown.enter.prevent="addDir"
                />
                <v-btn
                  color="secondary"
                  :loading="configSaving"
                  variant="tonal"
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
                  :color="dirChipColor(dirItem)"
                  variant="tonal"
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
            <v-chip color="primary" size="small" variant="tonal">
              {{ settingsState.section }}
            </v-chip>
            <v-chip :color="settingsState.legacy_flatten ? 'warning' : 'default'" size="small" variant="tonal">
              {{ settingsState.legacy_flatten ? t('plugins.settingsLegacy') : settingsSourceLabel(settingsState.config_source) }}
            </v-chip>
            <v-chip
              v-if="settingsPlugin?.admin_level"
              color="secondary"
              size="small"
              variant="tonal"
            >
              Lv.{{ settingsPlugin.admin_level }}
            </v-chip>
            <v-chip
              v-if="settingsPlugin?.plugin_type"
              :color="settingsPlugin.plugin_type === 'admin' || settingsPlugin.plugin_type === 'superuser' ? 'warning' : 'default'"
              size="small"
              variant="tonal"
            >
              {{ settingsPlugin.plugin_type }}
            </v-chip>
          </div>

          <div v-if="settingsPlugin" class="plugin-detail-meta">
            <div v-if="settingsPlugin.author || settingsPlugin.version" class="text-caption text-medium-emphasis">
              {{ settingsPlugin.author || 'unknown' }} · {{ settingsPlugin.version || '0.0.0' }}
            </div>
            <div v-if="settingsPlugin.required_plugins.length > 0" class="plugin-detail-tags">
              <span class="text-caption text-medium-emphasis">{{ t('plugins.requiredPlugins') }}</span>
              <v-chip
                v-for="dependency in settingsPlugin.required_plugins"
                :key="`detail-required:${dependency}`"
                color="info"
                size="x-small"
                variant="tonal"
              >
                {{ dependency }}
              </v-chip>
            </div>
            <div v-if="settingsPlugin.dependent_plugins.length > 0" class="plugin-detail-tags">
              <span class="text-caption text-medium-emphasis">{{ t('plugins.dependentPlugins') }}</span>
              <v-chip
                v-for="dependency in settingsPlugin.dependent_plugins"
                :key="`detail-dependent:${dependency}`"
                color="warning"
                size="x-small"
                variant="tonal"
              >
                {{ dependency }}
              </v-chip>
            </div>
          </div>

          <v-alert v-if="settingsErrorMessage" density="comfortable" type="error" variant="tonal">
            {{ settingsErrorMessage }}
          </v-alert>

          <v-progress-linear v-if="settingsDialogLoading" color="primary" indeterminate />

          <div v-if="!settingsDialogLoading" class="settings-shell">
            <div class="settings-shell__toolbar settings-shell__toolbar--dialog">
              <div class="settings-shell__headline" />
              <div class="settings-shell__actions">
                <v-btn-toggle
                  v-model="settingsEditorMode"
                  class="mode-switch"
                  color="primary"
                  density="comfortable"
                  divided
                  mandatory
                  variant="outlined"
                >
                  <v-btn value="basic">{{ t('plugins.settingsBasicTab') }}</v-btn>
                  <v-btn value="advanced">{{ t('plugins.settingsAdvancedTab') }}</v-btn>
                </v-btn-toggle>
                <v-btn
                  v-if="settingsEditorMode === 'basic'"
                  color="primary"
                  :disabled="!settingsState?.has_config_model || !hasPendingPluginChanges"
                  :loading="settingsSaving"
                  @click="openPluginSettingsPreview"
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
                      <v-chip color="secondary" size="x-small" variant="tonal">{{ field.editor }}</v-chip>
                      <v-chip :color="field.editable ? 'default' : 'warning'" size="x-small" variant="tonal">
                        {{ settingsValueSourceLabel(field.value_source) }}
                      </v-chip>
                      <v-chip v-if="field.choices.length > 0" color="secondary" size="x-small" variant="tonal">
                        {{ field.choices.join(', ') }}
                      </v-chip>
                    </div>
                  </div>

                  <div class="settings-list-row__actions">
                    <v-btn
                      v-if="!pluginEditor.isFieldEditing(field) && field.editable"
                      class="settings-action settings-action--primary"
                      color="primary"
                      size="small"
                      variant="tonal"
                      @click="pluginEditor.startOverride(field)"
                    >
                      {{ t('plugins.settingsAddOverride') }}
                    </v-btn>
                    <v-btn
                      v-if="pluginEditor.isFieldEditing(field)"
                      class="settings-action"
                      size="small"
                      variant="text"
                      @click="pluginEditor.cancelField(field)"
                    >
                      {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                      v-if="field.has_local_override"
                      class="settings-action"
                      color="warning"
                      :loading="settingsClearingKey === field.key"
                      size="small"
                      variant="text"
                      @click="clearPluginField(field)"
                    >
                      {{ t('plugins.settingsClear') }}
                    </v-btn>
                  </div>

                  <SettingsFieldEditor
                    v-model="settingsForm[field.key]"
                    :array-hint="t('plugins.settingsArrayHint')"
                    :editing="pluginEditor.isFieldEditing(field)"
                    :field="field"
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
                @save="openPluginRawPreview"
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

    <v-dialog v-model="previewDialogVisible" max-width="920">
      <v-card>
        <v-card-title>{{ previewTitle }}</v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <v-alert density="comfortable" type="warning" variant="tonal">
            {{ t('plugins.settingsRestartHint') }}
          </v-alert>
          <div v-if="previewMode === 'basic'" class="preview-list">
            <div
              v-for="item in previewItems"
              :key="item.key"
              class="preview-item"
            >
              <div class="preview-item__key">{{ item.key }}</div>
              <div class="preview-item__values">
                <div class="preview-item__block">
                  <div class="text-caption text-medium-emphasis">{{ t('plugins.previewCurrent') }}</div>
                  <pre class="preview-item__code">{{ item.current }}</pre>
                </div>
                <div class="preview-item__block">
                  <div class="text-caption text-medium-emphasis">{{ t('plugins.previewNext') }}</div>
                  <pre class="preview-item__code preview-item__code--next">{{ item.next }}</pre>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="preview-raw-grid">
            <div class="preview-item__block">
              <div class="text-caption text-medium-emphasis">{{ t('plugins.previewCurrent') }}</div>
              <pre class="preview-item__code">{{ previewCurrentText }}</pre>
            </div>
            <div class="preview-item__block">
              <div class="text-caption text-medium-emphasis">{{ t('plugins.previewNext') }}</div>
              <pre class="preview-item__code preview-item__code--next">{{ previewNextText }}</pre>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="previewDialogVisible = false">{{ t('common.cancel') }}</v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="previewSaving" @click="confirmPreviewSave">
            {{ t('plugins.confirmSave') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="toggleConfirmVisible" max-width="560">
      <v-card>
        <v-card-title>{{ toggleConfirmTitle }}</v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <v-alert density="comfortable" type="warning" variant="tonal">
            {{ toggleConfirmSummary }}
          </v-alert>
          <div v-if="toggleConfirmItem" class="confirm-plugin-list">
            <div class="confirm-plugin-item">
              <div class="confirm-plugin-item__title">
                <span class="font-weight-medium">{{ toggleConfirmItem.name || toggleConfirmItem.module_name }}</span>
                <span class="text-caption text-medium-emphasis">{{ toggleConfirmItem.module_name }}</span>
              </div>
              <div v-if="toggleConfirmItem.dependent_plugins.length > 0" class="confirm-plugin-item__relations">
                <v-chip
                  v-for="dependent in toggleConfirmItem.dependent_plugins"
                  :key="`confirm-dependent:${toggleConfirmItem.module_name}:${dependent}`"
                  color="warning"
                  size="x-small"
                  variant="tonal"
                >
                  {{ t('plugins.requiredBy', { name: dependent }) }}
                </v-chip>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="closeToggleConfirm">{{ t('common.cancel') }}</v-btn>
          <v-spacer />
          <v-btn color="warning" :loading="toggleConfirmLoading" @click="confirmToggleAction">
            {{ t('plugins.confirmDisable') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
  import {
    type DirConfigItem,
    getPluginConfig,
    getPlugins,
    getPluginSettings,
    getPluginSettingsRaw,
    type ModuleConfigItem,
    type PluginItem,
    type RawSettingsResponse,
    updatePlugin,
    updatePluginConfig,
    updatePluginSettings,
    updatePluginSettingsRaw,
  } from '@/api'
  import { getErrorMessage } from '@/api/client'
  import { useNoticeStore } from '@/stores/notice'
  import {
    buildChangedValues,
    displayFieldValue,
    type PluginSettingField,
  } from '@/views/plugins/settingsEditor'
  import RawSettingsEditor from '@/views/plugins/RawSettingsEditor.vue'
  import SettingsFieldEditor from '@/views/plugins/SettingsFieldEditor.vue'
  import { useSettingsEditor } from '@/views/plugins/useSettingsEditor'

  const plugins = ref<PluginItem[]>([])
  const loading = ref(false)
  const pendingModule = ref('')
  const errorMessage = ref('')
  const hideSystemPlugins = ref(true)
  const pluginSearch = ref('')
  const configSaving = ref(false)
  const pluginModules = ref<ModuleConfigItem[]>([])
  const pluginDirs = ref<DirConfigItem[]>([])
  const newModule = ref('')
  const newDir = ref('')
  const settingsDialogVisible = ref(false)
  const settingsLoadingModule = ref('')
  const settingsPlugin = ref<PluginItem | null>(null)
  const settingsEditorMode = ref<'basic' | 'advanced'>('basic')
  const settingsRawText = ref('')
  const settingsRawInitialText = ref('')
  const settingsRawLoading = ref(false)
  const settingsRawSaving = ref(false)
  const settingsRawErrorMessage = ref('')
  const previewDialogVisible = ref(false)
  const previewMode = ref<'basic' | 'raw'>('basic')
  const previewAction = ref<'plugin-basic' | 'plugin-raw'>('plugin-basic')
  const toggleConfirmVisible = ref(false)
  const toggleConfirmLoading = ref(false)
  const toggleConfirmItem = ref<PluginItem | null>(null)
  const noticeStore = useNoticeStore()
  const { t } = useI18n()
  const route = useRoute()

  const pluginEditor = useSettingsEditor({
    save: values => updatePluginSettings(settingsPlugin.value!.module_name, { values }),
    clear: key => updatePluginSettings(settingsPlugin.value!.module_name, { values: {}, clear: [key] }),
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
  const settingsFields = pluginEditor.fields
  const settingsForm = pluginEditor.form
  const hasPendingPluginChanges = pluginEditor.hasPendingChanges
  const hasPendingPluginRawChanges = computed(() => settingsRawText.value !== settingsRawInitialText.value)
  const previewSaving = computed(() => settingsSaving.value || settingsRawSaving.value)
  const previewTitle = computed(() =>
    previewMode.value === 'basic' ? t('plugins.previewChangesTitle') : t('plugins.previewRawTitle'),
  )
  const previewCurrentText = computed(() => settingsRawInitialText.value)
  const previewNextText = computed(() => settingsRawText.value)
  const previewItems = computed(() =>
    buildPreviewItems(settingsFields.value, settingsForm.value, pluginEditor.draftOverrides.value),
  )
  const toggleConfirmTitle = computed(() => t('plugins.disableConfirmTitle'))
  const toggleConfirmSummary = computed(() => {
    if (!toggleConfirmItem.value) return ''
    const riskCount = toggleConfirmItem.value.dependent_plugins.length
    if (riskCount > 0) {
      return t('plugins.disableConfirmRiskSummary', { count: 1, riskCount })
    }
    return t('plugins.disableConfirmSummary', { count: 1 })
  })

  const pluginHeaders = computed(() => [
    { title: t('plugins.name'), key: 'name' },
    { title: t('plugins.source'), key: 'source' },
    { title: t('plugins.enabled'), key: 'is_global_enabled', sortable: false, align: 'end' as const },
  ])

  const systemPlugins = computed(() =>
    plugins.value.filter(item => item.source === 'framework'),
  )

  const nonSystemPlugins = computed(() =>
    plugins.value.filter(item => !systemPlugins.value.some(systemItem => systemItem.module_name === item.module_name)),
  )

  const visiblePlugins = computed(() =>
    (hideSystemPlugins.value ? nonSystemPlugins.value : plugins.value)
      .filter(item => {
        if (route.query.enabled === 'disabled' && item.is_global_enabled) {
          return false
        }
        const keyword = pluginSearch.value.trim().toLowerCase()
        if (!keyword) return true
        return `${item.name || ''} ${item.module_name} ${item.description || ''} ${item.source}`.toLowerCase().includes(keyword)
      }),
  )

  const SOURCE_COLORS: Record<string, string> = {
    framework: 'error',
    official: 'primary',
    custom: 'success',
    builtin: 'secondary',
    external: 'warning',
  }

  function normalizeConfigEntry (value: string) {
    const normalized = value.trim()
    if (!normalized) return ''
    if (['none', 'null'].includes(normalized.toLowerCase())) return ''
    return normalized
  }

  function normalizeConfigEntries (values: string[]) {
    return Array.from(new Set(values.map(normalizeConfigEntry).filter(Boolean))).sort()
  }

  function applyRouteFilters () {
    const searchQuery = route.query.search
    pluginSearch.value = typeof searchQuery === 'string' ? searchQuery : ''
  }

  function buildPreviewItems (
    fields: PluginSettingField[],
    form: Record<string, unknown>,
    draftOverrides: Record<string, boolean>,
  ) {
    try {
      const editableFields = fields.filter(field =>
        field.editable && (field.has_local_override || Boolean(draftOverrides[field.key])),
      )
      const values = buildChangedValues(editableFields, form, t('plugins.settingsInvalidJson'))
      return editableFields
        .filter(field => Object.prototype.hasOwnProperty.call(values, field.key))
        .map(field => ({
          key: field.key,
          current: displayFieldValue(field.current_value),
          next: displayFieldValue(values[field.key]),
        }))
    } catch {
      return []
    }
  }

  function sourceColor (source: string) {
    return SOURCE_COLORS[source] || 'default'
  }

  function labelFromMap (source: string, map: Record<string, string>) {
    return map[source] || source
  }

  function sourceLabel (source: string) {
    return labelFromMap(source, {
      framework: t('plugins.framework'),
      official: t('plugins.official'),
      custom: t('plugins.custom'),
      builtin: t('plugins.builtin'),
      external: t('plugins.external'),
    })
  }

  function pluginMetaSummary (item: PluginItem) {
    const author = item.author?.trim()
    const version = item.version?.trim()
    if (author && version) return `${author} · ${version}`
    if (author) return author
    if (version) return `v${version}`
    return ''
  }

  function pluginRiskLabel (item: PluginItem) {
    if (item.is_protected && item.protected_reason) return item.protected_reason
    if (item.dependent_plugins.length > 0) {
      return t('plugins.dependentCountHint', { count: item.dependent_plugins.length })
    }
    if (item.required_plugins.length > 0) {
      return t('plugins.requiredCountHint', { count: item.required_plugins.length })
    }
    return ''
  }

  function settingsSourceLabel (source: string) {
    return labelFromMap(source, {
      static_scan: t('plugins.settingsSourceStaticScan'),
      plugin_metadata: t('plugins.settingsSourceMetadata'),
      none: t('plugins.settingsSourceNone'),
      manual: t('plugins.settingsSourceManual'),
      built_in: t('plugins.settingsSourceBuiltIn'),
    })
  }

  function settingsValueSourceLabel (source: string) {
    return labelFromMap(source, {
      default: t('plugins.settingsValueSourceDefault'),
      plugin_section: t('plugins.settingsValueSourcePlugin'),
      legacy_global: t('plugins.settingsValueSourceLegacy'),
      env: t('plugins.settingsValueSourceEnv'),
    })
  }

  function closeToggleConfirm () {
    toggleConfirmVisible.value = false
    toggleConfirmLoading.value = false
    toggleConfirmItem.value = null
  }

  function shouldConfirmToggle (item: PluginItem, enabled: boolean) {
    return !enabled && item.dependent_plugins.length > 0
  }

  function openToggleConfirm (item: PluginItem) {
    toggleConfirmItem.value = item
    toggleConfirmVisible.value = true
  }

  function applyPluginRawState (nextState: RawSettingsResponse) {
    settingsRawText.value = nextState.text
    settingsRawInitialText.value = nextState.text
  }

  async function loadPluginRawSettings (moduleName: string) {
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

  async function loadPluginManagement () {
    loading.value = true
    errorMessage.value = ''
    try {
      const [pluginsResponse, pluginConfigResponse] = await Promise.all([
        getPlugins(),
        getPluginConfig(),
      ])
      plugins.value = pluginsResponse.data
      pluginModules.value = pluginConfigResponse.data.modules
      pluginDirs.value = pluginConfigResponse.data.dirs
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('plugins.loadFailed'))
    } finally {
      loading.value = false
    }
  }

  async function openSettings (item: PluginItem) {
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

  async function saveSettings () {
    if (!settingsPlugin.value || !settingsState.value) return
    await pluginEditor.submit()
  }

  function openPluginSettingsPreview () {
    if (!settingsState.value) return
    const items = buildPreviewItems(settingsFields.value, settingsForm.value, pluginEditor.draftOverrides.value)
    if (items.length === 0) return
    previewMode.value = 'basic'
    previewAction.value = 'plugin-basic'
    previewDialogVisible.value = true
  }

  async function clearPluginField (field: PluginSettingField) {
    if (!settingsPlugin.value) return
    await pluginEditor.clearField(field)
  }

  async function savePluginRawSettings () {
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

  function openPluginRawPreview () {
    if (!hasPendingPluginRawChanges.value) return
    previewMode.value = 'raw'
    previewAction.value = 'plugin-raw'
    previewDialogVisible.value = true
  }

  async function confirmPreviewSave () {
    if (previewAction.value === 'plugin-basic') {
      await saveSettings()
    } else {
      await savePluginRawSettings()
    }

    if (!settingsErrorMessage.value && !settingsRawErrorMessage.value) {
      previewDialogVisible.value = false
    }
  }

  async function savePluginConfig (modules: string[], dirs: string[]) {
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

  async function addModule () {
    if (!newModule.value) return
    const nextModules = normalizeConfigEntries([
      ...pluginModules.value.map(item => item.name),
      newModule.value,
    ])
    newModule.value = ''
    await savePluginConfig(nextModules, normalizeConfigEntries(pluginDirs.value.map(item => item.path)))
  }

  async function removeModule (moduleName: string) {
    await savePluginConfig(
      pluginModules.value.filter(item => item.name !== moduleName).map(item => item.name),
      normalizeConfigEntries(pluginDirs.value.map(item => item.path)),
    )
  }

  async function addDir () {
    if (!newDir.value) return
    const nextDirs = normalizeConfigEntries([
      ...pluginDirs.value.map(item => item.path),
      newDir.value,
    ])
    newDir.value = ''
    await savePluginConfig(pluginModules.value.map(item => item.name), nextDirs)
  }

  async function removeDir (dirName: string) {
    await savePluginConfig(
      pluginModules.value.map(item => item.name),
      normalizeConfigEntries(
        pluginDirs.value.filter(item => item.path !== dirName).map(item => item.path),
      ),
    )
  }

  function moduleChipColor (item: ModuleConfigItem) {
    if (item.is_loaded) return 'success'
    if (item.is_importable) return 'warning'
    return 'error'
  }

  function dirChipColor (item: DirConfigItem) {
    if (!item.exists) return 'error'
    if (item.is_loaded) return 'success'
    return 'warning'
  }

  function moduleStatusText (item: ModuleConfigItem) {
    if (item.is_loaded) return t('plugins.moduleLoaded')
    if (item.is_importable) return t('plugins.moduleRegisteredOnly')
    return t('plugins.moduleMissing')
  }

  function dirStatusText (item: DirConfigItem) {
    if (!item.exists) return t('plugins.dirMissing')
    if (item.is_loaded) return t('plugins.dirLoaded')
    return t('plugins.dirRegisteredOnly')
  }

  async function togglePlugin (item: PluginItem, nextValue: boolean | null) {
    if (item.is_protected) {
      noticeStore.show(item.protected_reason || t('plugins.cannotDisable'), 'warning')
      return
    }
    const enabled = Boolean(nextValue)
    if (shouldConfirmToggle(item, enabled)) {
      item.is_global_enabled = !enabled
      openToggleConfirm(item)
      return
    }
    await executeToggle(item, enabled)
  }

  async function executeToggle (item: PluginItem, enabled: boolean) {
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

  async function confirmToggleAction () {
    if (!toggleConfirmItem.value) return
    toggleConfirmLoading.value = true
    try {
      await executeToggle(toggleConfirmItem.value, false)
      closeToggleConfirm()
    } finally {
      toggleConfirmLoading.value = false
    }
  }

  onMounted(() => {
    applyRouteFilters()
    void loadPluginManagement()
  })

  watch(() => route.query, () => {
    applyRouteFilters()
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

.settings-list-row__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

.settings-action {
  min-width: 68px;
}

.settings-action--primary {
  font-weight: 600;
}

.settings-list-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  line-height: 1.35;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.section-heading__main,
.section-heading__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.plugin-search {
  width: 240px;
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

.plugin-status-card {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.plugin-status-card__toolbar {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-height: 36px;
}

.plugin-status-card__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.plugin-status-card__toolbar :deep(.v-btn) {
  min-width: 44px;
  padding-inline: 4px;
}

.plugin-status-card__toolbar :deep(.v-switch) {
  width: 54px;
  margin-inline: 0;
}

.plugin-status-card__toolbar :deep(.v-chip) {
  min-width: 64px;
  justify-content: center;
}

.plugin-status-card__protected-chip {
  min-width: 0;
}

.plugin-status-card__hint {
  width: 100%;
  text-align: right;
  line-height: 1.35;
}

.plugins-table__name {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plugins-table__title-row,
.plugins-table__relations,
.plugin-detail-tags,
.confirm-plugin-item__relations {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.plugins-table__description,
.plugins-table__meta {
  line-height: 1.35;
}

.plugin-config-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.plugin-config-section__title {
  font-weight: 600;
}

.plugin-config-section__toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.plugin-detail-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.02);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.preview-item__key {
  font-weight: 600;
}

.preview-item__values,
.preview-raw-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.preview-item__block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-item__code {
  margin: 0;
  min-height: 72px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.preview-item__code--next {
  border-color: rgba(var(--v-theme-primary), 0.35);
}

.confirm-plugin-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.confirm-plugin-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.02);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.confirm-plugin-item__title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

@media (max-width: 960px) {
  .settings-list-row__main,
  .preview-item__values,
  .preview-raw-grid {
    grid-template-columns: 1fr;
  }

  .plugin-status-card__toolbar {
    justify-content: flex-end;
  }
}
</style>
