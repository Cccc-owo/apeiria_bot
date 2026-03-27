<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('core.title') }}</h1>
      <div class="page-actions">
        <v-btn :loading="loading" variant="tonal" @click="loadCoreManagement">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
      {{ errorMessage }}
    </v-alert>

    <v-card class="page-panel">
      <v-tabs v-model="sectionTab" color="primary">
        <v-tab value="core">{{ t('core.coreTab') }}</v-tab>
        <v-tab value="adapters">{{ t('core.adaptersTab') }}</v-tab>
        <v-tab value="drivers">{{ t('core.driversTab') }}</v-tab>
      </v-tabs>

      <v-divider />

      <v-window v-model="sectionTab">
        <v-window-item value="core">
          <v-card-text class="d-flex flex-column ga-3">
            <div class="settings-shell">
              <div class="settings-shell__toolbar">
                <div class="settings-shell__headline">
                  <div class="text-subtitle-1 font-weight-medium">{{ t('core.coreTab') }}</div>
                </div>
                <div class="settings-shell__actions">
                  <v-btn-toggle
                    v-model="coreEditorMode"
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
                    v-if="coreEditorMode === 'basic'"
                    color="primary"
                    :disabled="!hasPendingCoreChanges"
                    :loading="coreSaving"
                    @click="openCoreSettingsPreview"
                  >
                    {{ t('plugins.settingsSave') }}
                  </v-btn>
                </div>
              </div>

              <template v-if="coreEditorMode === 'basic'">
                <v-alert v-if="coreErrorMessage" density="comfortable" type="error" variant="tonal">
                  {{ coreErrorMessage }}
                </v-alert>

                <v-progress-linear v-if="coreLoading" color="primary" indeterminate />

                <div v-else class="settings-list-panel">
                  <div
                    v-for="field in coreFields"
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
                        v-if="!coreEditor.isFieldEditing(field) && field.editable"
                        class="settings-action settings-action--primary"
                        color="primary"
                        size="small"
                        variant="tonal"
                        @click="coreEditor.startOverride(field)"
                      >
                        {{ t('plugins.settingsAddOverride') }}
                      </v-btn>
                      <v-btn
                        v-if="coreEditor.isFieldEditing(field)"
                        class="settings-action"
                        size="small"
                        variant="text"
                        @click="coreEditor.cancelField(field)"
                      >
                        {{ t('common.cancel') }}
                      </v-btn>
                      <v-btn
                        v-if="field.has_local_override"
                        class="settings-action"
                        color="warning"
                        :loading="coreClearingKey === field.key"
                        size="small"
                        variant="text"
                        @click="clearCoreField(field)"
                      >
                        {{ t('plugins.settingsClear') }}
                      </v-btn>
                    </div>

                    <SettingsFieldEditor
                      v-model="coreForm[field.key]"
                      :array-hint="t('plugins.settingsArrayHint')"
                      :editing="coreEditor.isFieldEditing(field)"
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
                  v-model="coreRawText"
                  :description="t('plugins.settingsAdvancedDescription')"
                  :dirty="hasPendingCoreRawChanges"
                  :error-message="coreRawErrorMessage"
                  :loading="coreRawLoading"
                  :reload-label="t('common.refresh')"
                  :save-label="t('plugins.settingsSave')"
                  :saving="coreRawSaving"
                  @reload="loadCoreRawSettings"
                  @save="openCoreRawPreview"
                />
              </template>
            </div>
          </v-card-text>
        </v-window-item>

        <v-window-item value="adapters">
          <v-card-text class="d-flex flex-column ga-5">
            <div class="d-flex justify-space-between align-center flex-wrap ga-3">
              <div class="text-subtitle-1 font-weight-medium">{{ t('core.adaptersTab') }}</div>
              <v-sheet class="summary-card" rounded="lg">
                <div class="summary-card__label">{{ t('plugins.adapterCount') }}</div>
                <div class="summary-card__value">{{ adapterModules.length }}</div>
              </v-sheet>
            </div>
            <div class="config-chip-row">
              <v-chip
                v-for="adapterItem in adapterModules"
                :key="adapterItem.name"
                :color="moduleChipColor(adapterItem)"
                variant="tonal"
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
              <div class="text-subtitle-1 font-weight-medium">{{ t('core.driversTab') }}</div>
              <v-sheet class="summary-card" rounded="lg">
                <div class="summary-card__label">{{ t('plugins.driverCount') }}</div>
                <div class="summary-card__value">{{ driverBuiltin.length }}</div>
              </v-sheet>
            </div>
            <div class="config-chip-row">
              <v-chip
                v-for="driverItem in driverBuiltin"
                :key="driverItem.name"
                :color="driverChipColor(driverItem)"
                variant="tonal"
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

    <SettingsPreviewDialog
      v-model="previewDialogVisible"
      :cancel-label="t('common.cancel')"
      :confirm-label="t('plugins.confirmSave')"
      :current-label="t('plugins.previewCurrent')"
      :current-text="previewCurrentText"
      :items="previewItems"
      :mode="previewMode"
      :next-label="t('plugins.previewNext')"
      :next-text="previewNextText"
      :restart-hint="t('plugins.settingsRestartHint')"
      :saving="previewSaving"
      :title="previewTitle"
      @cancel="previewDialogVisible = false"
      @confirm="confirmPreviewSave"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
  import {
    type DriverConfigItem,
    getAdapterConfig,
    getCoreSettings,
    getCoreSettingsRaw,
    getDriverConfig,
    type ModuleConfigItem,
    type RawSettingsResponse,
    updateCoreSettings,
    updateCoreSettingsRaw,
  } from '@/api'
  import { getErrorMessage } from '@/api/client'
  import { useNoticeStore } from '@/stores/notice'
  import {
    buildSettingsPreviewItems,
    displayFieldValue,
    type PluginSettingField,
  } from '@/views/plugins/settingsEditor'
  import RawSettingsEditor from '@/views/plugins/RawSettingsEditor.vue'
  import SettingsFieldEditor from '@/views/plugins/SettingsFieldEditor.vue'
  import SettingsPreviewDialog from '@/views/plugins/SettingsPreviewDialog.vue'
  import { useSettingsEditor } from '@/views/plugins/useSettingsEditor'

  const loading = ref(false)
  const errorMessage = ref('')
  const sectionTab = ref('core')
  const adapterModules = ref<ModuleConfigItem[]>([])
  const driverBuiltin = ref<DriverConfigItem[]>([])
  const coreEditorMode = ref<'basic' | 'advanced'>('basic')
  const coreRawText = ref('')
  const coreRawInitialText = ref('')
  const coreRawLoading = ref(false)
  const coreRawSaving = ref(false)
  const coreRawErrorMessage = ref('')
  const previewDialogVisible = ref(false)
  const previewMode = ref<'basic' | 'raw'>('basic')
  const previewAction = ref<'core-basic' | 'core-raw'>('core-basic')
  const noticeStore = useNoticeStore()
  const { t } = useI18n()
  const route = useRoute()

  const coreEditor = useSettingsEditor({
    load: getCoreSettings,
    save: values => updateCoreSettings({ values }),
    clear: key => updateCoreSettings({ values: {}, clear: [key] }),
    messages: {
      clearSuccess: t('plugins.settingsCleared'),
      invalidJson: t('plugins.settingsInvalidJson'),
      loadFailed: t('plugins.settingsLoadFailed'),
      saveFailed: t('plugins.settingsSaveFailed'),
      saveSuccess: t('plugins.settingsSaved'),
    },
  })

  const coreLoading = coreEditor.loading
  const coreSaving = coreEditor.saving
  const coreClearingKey = coreEditor.clearingKey
  const coreErrorMessage = coreEditor.errorMessage
  const coreSettings = coreEditor.state
  const coreFields = coreEditor.fields
  const coreForm = coreEditor.form
  const hasPendingCoreChanges = coreEditor.hasPendingChanges
  const hasPendingCoreRawChanges = computed(() => coreRawText.value !== coreRawInitialText.value)
  const previewSaving = computed(() => coreSaving.value || coreRawSaving.value)
  const previewTitle = computed(() =>
    previewMode.value === 'basic' ? t('plugins.previewChangesTitle') : t('plugins.previewRawTitle'),
  )
  const previewCurrentText = computed(() => coreRawInitialText.value)
  const previewNextText = computed(() => coreRawText.value)
  const previewItems = computed(() =>
    buildSettingsPreviewItems(
      coreFields.value,
      coreForm.value,
      coreEditor.draftOverrides.value,
      t('plugins.settingsInvalidJson'),
    ),
  )

  function applyRouteFilters () {
    const sectionQuery = route.query.section
    if (
      sectionQuery === 'core'
      || sectionQuery === 'adapters'
      || sectionQuery === 'drivers'
    ) {
      sectionTab.value = sectionQuery
      return
    }
    sectionTab.value = 'core'
  }

  function settingsValueSourceLabel (source: string) {
    const map: Record<string, string> = {
      default: t('plugins.settingsValueSourceDefault'),
      plugin_section: t('plugins.settingsValueSourcePlugin'),
      legacy_global: t('plugins.settingsValueSourceLegacy'),
      env: t('plugins.settingsValueSourceEnv'),
    }
    return map[source] || source
  }

  function applyCoreRawState (nextState: RawSettingsResponse) {
    coreRawText.value = nextState.text
    coreRawInitialText.value = nextState.text
  }

  async function loadCoreRawSettings () {
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

  async function loadCoreManagement () {
    loading.value = true
    coreLoading.value = true
    coreRawLoading.value = true
    errorMessage.value = ''
    coreErrorMessage.value = ''
    coreRawErrorMessage.value = ''
    try {
      const [adapterConfigResponse, driverConfigResponse] = await Promise.all([
        getAdapterConfig(),
        getDriverConfig(),
      ])
      adapterModules.value = adapterConfigResponse.data.modules
      driverBuiltin.value = driverConfigResponse.data.builtin
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('core.loadFailed'))
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

  function moduleChipColor (item: ModuleConfigItem) {
    if (item.is_loaded) return 'success'
    if (item.is_importable) return 'warning'
    return 'error'
  }

  function moduleStatusText (item: ModuleConfigItem) {
    if (item.is_loaded) return t('plugins.moduleLoaded')
    if (item.is_importable) return t('plugins.moduleRegisteredOnly')
    return t('plugins.moduleMissing')
  }

  function driverChipColor (item: DriverConfigItem) {
    return item.is_active ? 'success' : 'warning'
  }

  function driverStatusText (item: DriverConfigItem) {
    return item.is_active ? t('plugins.driverActive') : t('plugins.driverRegisteredOnly')
  }

  async function clearCoreField (field: PluginSettingField) {
    await coreEditor.clearField(field)
  }

  async function saveCoreSettings () {
    if (!coreSettings.value) return
    await coreEditor.submit()
  }

  function openCoreSettingsPreview () {
    if (!coreSettings.value) return
    const items = previewItems.value
    if (items.length === 0) return
    previewMode.value = 'basic'
    previewAction.value = 'core-basic'
    previewDialogVisible.value = true
  }

  async function saveCoreRawSettings () {
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

  function openCoreRawPreview () {
    if (!hasPendingCoreRawChanges.value) return
    previewMode.value = 'raw'
    previewAction.value = 'core-raw'
    previewDialogVisible.value = true
  }

  async function confirmPreviewSave () {
    if (previewAction.value === 'core-basic') {
      await saveCoreSettings()
    } else {
      await saveCoreRawSettings()
    }

    if (!coreErrorMessage.value && !coreRawErrorMessage.value) {
      previewDialogVisible.value = false
    }
  }

  onMounted(() => {
    applyRouteFilters()
    void loadCoreManagement()
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

.config-chip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 32px;
}

@media (max-width: 960px) {
  .settings-list-row__main {
    grid-template-columns: 1fr;
  }
}
</style>
