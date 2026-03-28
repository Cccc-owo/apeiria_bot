<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('plugins.title') }}</h1>
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
            <v-btn
              v-if="authStore.role === 'owner'"
              color="primary"
              variant="tonal"
              @click="openManualInstallDialog"
            >
              {{ t('plugins.manualInstall') }}
            </v-btn>
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

        <div v-if="visiblePlugins.length > 0" class="plugins-grid">
          <article
            v-for="item in visiblePlugins"
            :key="item.module_name"
            class="plugin-card"
          >
            <div class="plugin-card__top">
              <div class="plugin-card__headline">
                <div class="plugin-card__title-row">
                  <h2 class="plugin-card__title">{{ item.name || item.module_name }}</h2>
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
                  <v-chip
                    v-if="item.is_protected"
                    color="warning"
                    size="x-small"
                    variant="tonal"
                  >
                    {{ t('plugins.protected') }}
                    <v-tooltip v-if="pluginToggleHint(item)" activator="parent" location="top">
                      {{ pluginToggleHint(item) }}
                    </v-tooltip>
                  </v-chip>
                </div>
                <div class="plugin-card__subline text-caption text-medium-emphasis">
                  {{ item.module_name }}
                </div>
                <div v-if="pluginMetaSummary(item)" class="plugin-card__subline text-caption text-medium-emphasis">
                  {{ pluginMetaSummary(item) }}
                </div>
              </div>

              <v-chip :color="sourceColor(item.source)" size="small" variant="tonal">
                {{ sourceLabel(item.source) }}
              </v-chip>
            </div>

            <p v-if="item.description" class="plugin-card__description">
              {{ item.description }}
            </p>

            <div
              v-if="item.required_plugins.length > 0 || item.dependent_plugins.length > 0"
              class="plugin-card__relations"
            >
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

            <div class="plugin-card__footer">
              <div class="plugin-card__footer-bar">
                <div class="plugin-card__actions">
                  <v-btn
                    v-if="canUninstallPlugin(item)"
                    color="warning"
                    :loading="uninstallingModule === item.module_name"
                    size="small"
                    variant="text"
                    @click="uninstallPluginItem(item)"
                  >
                    {{ t('plugins.settingsUninstall') }}
                  </v-btn>
                  <v-btn
                    v-if="pluginProjectUrl(item)"
                    color="primary"
                    :href="pluginProjectUrl(item)"
                    rel="noopener noreferrer"
                    size="small"
                    target="_blank"
                    variant="text"
                  >
                    {{ t('plugins.projectPage') }}
                  </v-btn>
                  <v-btn
                    color="primary"
                    :loading="settingsLoadingModule === item.module_name"
                    size="small"
                    variant="text"
                    @click="openSettings(item)"
                  >
                    {{ t('plugins.settings') }}
                  </v-btn>
                </div>
                <div class="plugin-card__switch-wrap">
                  <v-switch
                    class="plugin-card__switch"
                    color="success"
                    :disabled="item.is_protected"
                    hide-details
                    inset
                    :loading="pendingModule === item.module_name"
                    :model-value="item.is_global_enabled"
                    @update:model-value="togglePlugin(item, $event)"
                  />
                  <v-tooltip v-if="pluginToggleHint(item)" activator="parent" location="top">
                    {{ pluginToggleHint(item) }}
                  </v-tooltip>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div v-else class="py-6 text-body-2 text-medium-emphasis text-center">
          {{ t('plugins.noVisiblePlugins') }}
        </div>
      </v-card-text>
    </v-card>

    <v-dialog v-model="settingsDialogVisible" max-width="920">
      <v-card class="settings-dialog-card">
        <v-card-title class="settings-dialog-header">
          <div class="settings-dialog-header__main">
            <div class="settings-dialog-header__title-block">
              <span class="settings-dialog-header__title">
                {{ t('plugins.settingsTitle', { name: settingsPlugin?.name || settingsPlugin?.module_name || '' }) }}
              </span>
              <span class="settings-dialog-header__module text-caption text-medium-emphasis">
                {{ settingsPlugin?.module_name }}
              </span>
            </div>

            <div class="settings-dialog-header__meta">
              <v-chip v-if="settingsState" color="primary" size="small" variant="tonal">
                {{ settingsState.section }}
              </v-chip>
              <v-chip
                v-if="settingsState"
                :color="settingsState.legacy_flatten ? 'warning' : 'default'"
                size="small"
                variant="tonal"
              >
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
              <span v-if="settingsPlugin" class="settings-dialog-header__summary text-caption text-medium-emphasis">
                {{ pluginMetaSummary(settingsPlugin) || 'unknown' }}
              </span>
              <span
                v-if="settingsPlugin?.installed_package"
                class="settings-dialog-header__summary text-caption text-medium-emphasis"
              >
                {{ t('plugins.settingsInstalledPackage') }}: {{ settingsPlugin.installed_package }}
              </span>
            </div>

            <div
              v-if="settingsPlugin && (settingsPlugin.required_plugins.length > 0 || settingsPlugin.dependent_plugins.length > 0)"
              class="settings-dialog-header__relations"
            >
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
          </div>

        </v-card-title>
        <v-card-text class="settings-dialog-card__body d-flex flex-column ga-4">
          <v-alert v-if="settingsErrorMessage" density="comfortable" type="error" variant="tonal">
            {{ settingsErrorMessage }}
          </v-alert>

          <v-progress-linear v-if="settingsDialogLoading" color="primary" indeterminate />

          <div v-if="!settingsDialogLoading" class="settings-shell settings-shell--dialog">
            <SettingsModeBar
              v-model="settingsEditorMode"
              :advanced-label="t('plugins.settingsAdvancedTab')"
              :basic-label="t('plugins.settingsBasicTab')"
              :tablist-label="t('plugins.settingsTitle')"
            >
              <template #actions>
                <v-btn
                  v-if="settingsEditorMode === 'basic'"
                  color="primary"
                  :disabled="!settingsState?.has_config_model || !hasPendingPluginChanges"
                  :loading="settingsSaving"
                  @click="openPluginSettingsPreview"
                >
                  {{ t('plugins.settingsSave') }}
                </v-btn>
              </template>
            </SettingsModeBar>

            <template v-if="settingsEditorMode === 'basic'">
              <div v-if="!settingsState?.has_config_model || settingsFields.length === 0" class="text-body-2 text-medium-emphasis">
                {{ t('plugins.settingsEmpty') }}
              </div>

              <div v-else class="settings-list-panel">
                <section
                  v-for="field in settingsFields"
                  :key="field.key"
                  class="settings-list-row"
                >
                  <div class="settings-list-row__main">
                    <div class="settings-list-row__info">
                      <div class="settings-list-row__label text-subtitle-2 font-weight-medium">
                        {{ field.key }}
                      </div>
                      <div v-if="field.help" class="settings-list-row__description text-caption text-medium-emphasis">
                        {{ field.help }}
                      </div>
                      <div class="settings-list-row__status">
                        <v-chip
                          v-if="field.has_local_override || pluginEditor.isFieldEditing(field)"
                          color="primary"
                          size="x-small"
                          variant="tonal"
                        >
                          {{ t('plugins.settingsLocalShort') }}
                        </v-chip>
                        <v-chip
                          v-if="!field.editable"
                          color="warning"
                          size="x-small"
                          variant="tonal"
                        >
                          {{ t('plugins.settingsReadonly') }}
                        </v-chip>
                      </div>
                      <div class="settings-list-row__meta text-caption text-medium-emphasis">
                        <span>{{ t('plugins.settingsType') }}: {{ field.type }}</span>
                        <span>{{ t('plugins.settingsValueSource') }}: {{ settingsValueSourceLabel(field.value_source) }}</span>
                        <span v-if="field.global_key">{{ t('plugins.settingsGlobalKey') }}: {{ field.global_key }}</span>
                        <span v-if="field.choices.length > 0">{{ t('plugins.settingsChoices') }}: {{ formatFieldChoices(field.choices) }}</span>
                      </div>
                    </div>

                    <div class="settings-list-row__control">
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
                    </div>
                  </div>
                </section>
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
                :validation-error-column="pluginRawValidationColumn"
                :validation-error-line="pluginRawValidationLine"
                :validation-error-message="pluginRawValidationMessage"
                :validation-pending="pluginRawValidationPending"
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

    <v-dialog v-model="manualInstallDialogVisible" max-width="640">
      <v-card rounded="xl">
        <v-card-title>{{ t('plugins.manualInstall') }}</v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <v-alert density="comfortable" type="info" variant="tonal">
            {{ t('plugins.manualInstallHint') }}
          </v-alert>
          <v-select
            v-model="manualInstallSourceType"
            density="comfortable"
            hide-details
            item-title="label"
            item-value="value"
            :items="manualInstallSourceOptions"
            :label="t('plugins.manualInstallSourceType')"
          />
          <v-text-field
            v-model.trim="manualInstallRequirement"
            density="comfortable"
            :hint="manualInstallRequirementHint"
            :label="manualInstallRequirementLabel"
            persistent-hint
          />
          <v-text-field
            v-model.trim="manualInstallModuleName"
            density="comfortable"
            :hint="t('plugins.manualInstallModuleHint')"
            :label="t('plugins.manualInstallModule')"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-btn rounded="xl" variant="text" @click="manualInstallDialogVisible = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn
            color="primary"
            :disabled="!canSubmitManualInstall"
            :loading="manualInstallSubmitting"
            rounded="xl"
            @click="submitManualInstall"
          >
            {{ t('plugins.manualInstallSubmit') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="manualInstallTaskDialogVisible" max-width="840">
      <v-card rounded="xl">
        <v-card-title>{{ manualInstallTask?.title || t('plugins.manualInstallTaskTitle') }}</v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <div class="text-body-2 text-medium-emphasis">
            {{ manualInstallTaskStatusLabel }}
          </div>
          <v-alert
            v-if="manualInstallTaskErrorSummary"
            density="comfortable"
            type="error"
            variant="tonal"
          >
            {{ manualInstallTaskErrorSummary }}
          </v-alert>
          <v-progress-linear
            v-if="manualInstallTask?.status === 'pending' || manualInstallTask?.status === 'running'"
            color="primary"
            indeterminate
          />
          <v-sheet class="task-log-card" rounded="lg">
            <pre class="task-log-card__content">{{ manualInstallTask?.logs || t('plugins.manualInstallWaiting') }}</pre>
          </v-sheet>
        </v-card-text>
        <v-card-actions>
          <v-btn rounded="xl" variant="text" @click="manualInstallTaskDialogVisible = false">
            {{ t('common.close') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
  import {
    getPluginInstallTask,
    getPlugins,
    getPluginSettings,
    getPluginSettingsRaw,
    installManualPlugin,
    type PluginItem,
    type PluginStoreTask,
    type RawSettingsResponse,
    uninstallPlugin,
    updatePlugin,
    updatePluginSettings,
    updatePluginSettingsRaw,
    validatePluginSettingsRaw,
  } from '@/api'
  import { getErrorMessage } from '@/api/client'
  import { useAuthStore } from '@/stores/auth'
  import { useNoticeStore } from '@/stores/notice'
  import { useRestartStore } from '@/stores/restart'
  import {
    buildRevertValues,
    buildSettingsPreviewItems,
    displayFieldValue,
    type PluginSettingField,
  } from '@/views/plugins/settingsEditor'
  import RawSettingsEditor from '@/views/plugins/RawSettingsEditor.vue'
  import SettingsFieldEditor from '@/views/plugins/SettingsFieldEditor.vue'
  import SettingsModeBar from '@/views/plugins/SettingsModeBar.vue'
  import SettingsPreviewDialog from '@/views/plugins/SettingsPreviewDialog.vue'
  import { useSettingsEditor } from '@/views/plugins/useSettingsEditor'
  import { useRawTomlValidation } from '@/composables/useRawTomlValidation'

  const plugins = ref<PluginItem[]>([])
  const loading = ref(false)
  const pendingModule = ref('')
  const errorMessage = ref('')
  const hideSystemPlugins = ref(true)
  const pluginSearch = ref('')
  const manualInstallDialogVisible = ref(false)
  const manualInstallTaskDialogVisible = ref(false)
  const manualInstallSubmitting = ref(false)
  const manualInstallSourceType = ref<'pypi' | 'git' | 'local'>('pypi')
  const manualInstallRequirement = ref('')
  const manualInstallModuleName = ref('')
  const manualInstallTask = ref<PluginStoreTask | null>(null)
  const activeManualInstallRequirement = ref('')
  let manualInstallTaskPollTimer: number | null = null
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
  const uninstallingModule = ref('')
  const authStore = useAuthStore()
  const noticeStore = useNoticeStore()
  const restartStore = useRestartStore()
  const { t } = useI18n()
  const route = useRoute()

  const pluginEditor = useSettingsEditor({
    save: payload => updatePluginSettings(settingsPlugin.value!.module_name, payload),
    messages: {
      invalidJson: t('plugins.settingsInvalidJson'),
      loadFailed: t('plugins.settingsLoadFailed'),
      saveFailed: t('plugins.settingsSaveFailed'),
      saveSuccess: t('plugins.settingsSaved'),
    },
    afterSave: ({ previousState, values, clear }) => {
      if (!settingsPlugin.value) return
      restartStore.markPending({
        id: `plugin:settings:${settingsPlugin.value.module_name}`,
        scope: 'plugins',
        summary: t('restart.pendingPluginSettings', {
          name: settingsPlugin.value.name || settingsPlugin.value.module_name,
        }),
        undo: {
          kind: 'plugin-settings',
          moduleName: settingsPlugin.value.module_name,
          values: buildRevertValues(previousState.fields, values, clear),
        },
      })
    },
  })

  const settingsDialogLoading = pluginEditor.loading
  const settingsSaving = pluginEditor.saving
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
    buildSettingsPreviewItems(
      settingsFields.value,
      settingsForm.value,
      pluginEditor.draftOverrides.value,
      pluginEditor.draftClears.value,
      t('plugins.settingsInvalidJson'),
    ),
  )
  const {
    validateNow: validatePluginRawNow,
    validationColumn: pluginRawValidationColumn,
    validationLine: pluginRawValidationLine,
    validationMessage: pluginRawValidationMessage,
    validationPending: pluginRawValidationPending,
  } = useRawTomlValidation({
    text: settingsRawText,
    initialText: settingsRawInitialText,
    fallbackMessage: t('plugins.settingsRawValidateFailed'),
    validate: async text => {
      if (!settingsPlugin.value) {
        return { valid: true, message: null, line: null, column: null }
      }
      return (await validatePluginSettingsRaw(settingsPlugin.value.module_name, { text })).data
    },
  })
  const toggleConfirmTitle = computed(() => t('plugins.disableConfirmTitle'))
  const toggleConfirmSummary = computed(() => {
    if (!toggleConfirmItem.value) return ''
    const riskCount = toggleConfirmItem.value.dependent_plugins.length
    if (riskCount > 0) {
      return t('plugins.disableConfirmRiskSummary', { count: 1, riskCount })
    }
    return t('plugins.disableConfirmSummary', { count: 1 })
  })
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

  const manualInstallSourceOptions = computed(() => [
    { value: 'pypi', label: t('plugins.manualInstallSourcePypi') },
    { value: 'git', label: t('plugins.manualInstallSourceGit') },
    { value: 'local', label: t('plugins.manualInstallSourceLocal') },
  ])

  const manualInstallRequirementLabel = computed(() => {
    if (manualInstallSourceType.value === 'git') {
      return t('plugins.manualInstallGitLabel')
    }
    if (manualInstallSourceType.value === 'local') {
      return t('plugins.manualInstallLocalLabel')
    }
    return t('plugins.manualInstallPackageLabel')
  })

  const manualInstallRequirementHint = computed(() => {
    if (manualInstallSourceType.value === 'git') {
      return t('plugins.manualInstallGitHint')
    }
    if (manualInstallSourceType.value === 'local') {
      return t('plugins.manualInstallLocalHint')
    }
    return t('plugins.manualInstallPackageHint')
  })

  const canSubmitManualInstall = computed(() => manualInstallRequirement.value.trim().length > 0)
  const manualInstallTaskErrorSummary = computed(() => {
    const error = manualInstallTask.value?.error?.trim()
    if (!error) return ''
    return error.split('\n')[0]?.trim() || error
  })
  const manualInstallTaskStatusLabel = computed(() => {
    const status = manualInstallTask.value?.status || ''
    if (status === 'pending') return t('plugins.manualInstallPending')
    if (status === 'running') return t('plugins.manualInstallRunning')
    if (status === 'succeeded') return t('plugins.manualInstallSucceeded')
    if (status === 'failed') return manualInstallTaskErrorSummary.value || t('plugins.manualInstallFailed')
    return ''
  })

  function applyRouteFilters () {
    const searchQuery = route.query.search
    pluginSearch.value = typeof searchQuery === 'string' ? searchQuery : ''
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

  function pluginToggleHint (item: PluginItem) {
    if (item.is_protected && item.protected_reason) return item.protected_reason
    return ''
  }

  function pluginProjectUrl (item: PluginItem) {
    const candidate = item.homepage || ''
    if (candidate.startsWith('http://') || candidate.startsWith('https://')) {
      return candidate
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

  function formatFieldChoices (choices: unknown[]) {
    const normalized = choices
      .map(choice => displayFieldValue(choice))
      .filter(Boolean)

    if (normalized.length <= 4) {
      return normalized.join(' / ')
    }

    return `${normalized.slice(0, 4).join(' / ')} +${normalized.length - 4}`
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
      plugins.value = (await getPlugins()).data
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('plugins.loadFailed'))
    } finally {
      loading.value = false
    }
  }

  function openManualInstallDialog () {
    manualInstallSourceType.value = 'pypi'
    manualInstallRequirement.value = ''
    manualInstallModuleName.value = ''
    manualInstallDialogVisible.value = true
  }

  async function submitManualInstall () {
    const requirement = manualInstallRequirement.value.trim()
    if (!requirement) return

    manualInstallSubmitting.value = true
    try {
      const response = await installManualPlugin({
        requirement,
        module_name: manualInstallModuleName.value.trim() || undefined,
      })
      activeManualInstallRequirement.value = requirement
      manualInstallTask.value = response.data
      manualInstallDialogVisible.value = false
      manualInstallTaskDialogVisible.value = true
      startManualInstallTaskPolling(response.data.task_id)
    } catch (error) {
      noticeStore.show(getErrorMessage(error, t('plugins.manualInstallFailed')), 'error')
    } finally {
      manualInstallSubmitting.value = false
    }
  }

  function stopManualInstallTaskPolling () {
    if (manualInstallTaskPollTimer !== null) {
      window.clearInterval(manualInstallTaskPollTimer)
      manualInstallTaskPollTimer = null
    }
  }

  function startManualInstallTaskPolling (taskId: string) {
    stopManualInstallTaskPolling()
    manualInstallTaskPollTimer = window.setInterval(async () => {
      try {
        const response = await getPluginInstallTask(taskId)
        manualInstallTask.value = response.data
        if (response.data.status === 'succeeded' || response.data.status === 'failed') {
          stopManualInstallTaskPolling()
          if (response.data.status === 'succeeded') {
            const moduleName = typeof response.data.result.module_name === 'string'
              ? response.data.result.module_name
              : ''
            const requirement = typeof response.data.result.requirement === 'string'
              ? response.data.result.requirement
              : activeManualInstallRequirement.value
            restartStore.markPending({
              id: `plugin-manual-install:${moduleName || requirement}`,
              scope: 'plugins',
              summary: t('plugins.manualInstallRestartPending', { name: moduleName || requirement }),
              undo: {
                kind: 'plugin-install',
                packageName: requirement,
                moduleName,
              },
            })
            noticeStore.show(t('plugins.manualInstallSucceeded'), 'success')
            void loadPluginManagement()
          } else {
            noticeStore.show(summarizeTaskError(response.data.error) || t('plugins.manualInstallFailed'), 'error')
          }
        }
      } catch (error) {
        stopManualInstallTaskPolling()
        noticeStore.show(getErrorMessage(error, t('plugins.manualInstallFailed')), 'error')
      }
    }, 1500)
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

  function canUninstallPlugin (item: PluginItem) {
    return authStore.role === 'owner'
      && !item.is_protected
      && (item.source === 'custom' || item.source === 'external')
  }

  async function uninstallPluginItem (item: PluginItem) {
    const pluginName = item.name || item.module_name
    const confirmMessage = item.installed_package
      ? t('plugins.settingsUninstallConfirm', {
        name: pluginName,
        package: item.installed_package,
      })
      : t('plugins.settingsUninstallConfirmFallback', {
        name: pluginName,
      })
    if (!window.confirm(confirmMessage)) {
      return
    }

    uninstallingModule.value = item.module_name
    try {
      await uninstallPlugin(item.module_name)
      noticeStore.show(t('plugins.settingsUninstallSucceeded'), 'success')
      if (settingsPlugin.value?.module_name === item.module_name) {
        settingsDialogVisible.value = false
      }
      await loadPluginManagement()
    } catch (error) {
      noticeStore.show(getErrorMessage(error, t('plugins.settingsUninstallFailed')), 'error')
    } finally {
      uninstallingModule.value = ''
    }
  }

  function openPluginSettingsPreview () {
    if (!settingsState.value) return
    const items = previewItems.value
    if (items.length === 0) return
    previewMode.value = 'basic'
    previewAction.value = 'plugin-basic'
    previewDialogVisible.value = true
  }

  async function clearPluginField (field: PluginSettingField) {
    pluginEditor.clearField(field)
  }

  function summarizeTaskError (message: string | null | undefined) {
    const normalized = message?.trim()
    if (!normalized) return ''
    return normalized.split('\n')[0]?.trim() || normalized
  }

  async function savePluginRawSettings () {
    if (!settingsPlugin.value || !hasPendingPluginRawChanges.value) return
    settingsRawSaving.value = true
    settingsRawErrorMessage.value = ''
    const previousText = settingsRawInitialText.value
    try {
      const rawResponse = await updatePluginSettingsRaw(settingsPlugin.value.module_name, {
        text: settingsRawText.value,
      })
      const settingsResponse = await getPluginSettings(settingsPlugin.value.module_name)
      applyPluginRawState(rawResponse.data)
      pluginEditor.applyState(settingsResponse.data)
      restartStore.markPending({
        id: `plugin:raw:${settingsPlugin.value.module_name}`,
        scope: 'plugins',
        summary: t('restart.pendingPluginRaw', {
          name: settingsPlugin.value.name || settingsPlugin.value.module_name,
        }),
        undo: {
          kind: 'plugin-raw',
          moduleName: settingsPlugin.value.module_name,
          text: previousText,
        },
      })
      noticeStore.show(t('plugins.settingsRawSaved'), 'success')
    } catch (error) {
      const message = getErrorMessage(error, t('plugins.settingsRawSaveFailed'))
      settingsRawErrorMessage.value = message
      noticeStore.show(message, 'error')
    } finally {
      settingsRawSaving.value = false
    }
  }

  async function openPluginRawPreview () {
    if (!hasPendingPluginRawChanges.value) return
    if (!await validatePluginRawNow()) return
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
      restartStore.markPending({
        id: `plugin:toggle:${item.module_name}`,
        scope: 'plugins',
        summary: t('restart.pendingPluginToggle', {
          name: item.name || item.module_name,
        }),
        undo: {
          kind: 'plugin-toggle',
          moduleName: item.module_name,
          enabled: previous,
        },
      })
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

  onBeforeUnmount(() => {
    stopManualInstallTaskPolling()
  })
</script>

<style scoped>
.settings-dialog-card {
  display: flex;
  flex-direction: column;
  max-height: min(88vh, 920px);
}

.settings-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px 12px;
}

.settings-dialog-header__main {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  flex-direction: column;
  gap: 10px;
}

.settings-dialog-header__title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.settings-dialog-header__title {
  font-size: 1.2rem;
  line-height: 1.3;
  font-weight: 700;
}

.settings-dialog-header__module {
  line-height: 1.35;
}

.settings-dialog-header__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.settings-dialog-header__summary {
  margin-left: 4px;
  white-space: nowrap;
}

.settings-dialog-header__relations {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.settings-dialog-card__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  padding-top: 0;
}

.settings-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-shell--dialog {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.settings-list-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 14px;
}

.settings-shell--dialog .settings-list-panel {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.settings-list-row {
  padding: 18px 20px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background:
    linear-gradient(180deg, rgba(var(--v-theme-surface), 0.98), rgba(var(--v-theme-surface), 0.98)),
    linear-gradient(135deg, rgba(var(--v-theme-primary), 0.02), rgba(var(--v-theme-secondary), 0.02));
}

.settings-list-row:last-child {
  border-bottom: 0;
}

.settings-list-row__main {
  display: grid;
  grid-template-columns: minmax(200px, 260px) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.settings-list-row__info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.settings-list-row__label {
  line-height: 1.3;
  word-break: break-word;
}

.settings-list-row__description {
  line-height: 1.45;
}

.settings-list-row__status {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-height: 20px;
}

.settings-list-row__control {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  padding: 14px;
  border-radius: 14px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 1px solid rgba(var(--v-border-color), 0.65);
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
  gap: 6px 12px;
  line-height: 1.35;
  word-break: break-word;
}

.settings-list-row__control :deep(.settings-field-editor) {
  width: 100%;
}

.settings-list-row__control :deep(.v-field),
.settings-list-row__control :deep(.v-selection-control) {
  width: 100%;
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

.plugins-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.plugin-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 228px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background:
    linear-gradient(180deg, rgba(var(--v-theme-surface), 0.98), rgba(var(--v-theme-surface), 0.94)),
    linear-gradient(135deg, rgba(var(--v-theme-primary), 0.03), rgba(var(--v-theme-secondary), 0.03));
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
}

.plugin-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.plugin-card__headline {
  min-width: 0;
  display: flex;
  flex: 1 1 220px;
  flex-direction: column;
  gap: 4px;
}

.plugin-card__title-row,
.plugin-card__relations,
.plugin-detail-tags,
.confirm-plugin-item__relations {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.plugin-card__title {
  margin: 0;
  font-size: 1rem;
  line-height: 1.25;
  font-weight: 800;
}

.plugin-card__subline {
  line-height: 1.35;
}

.plugin-card__description {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.76);
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.plugin-card__footer {
  margin-top: auto;
}

.plugin-card__footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.plugin-card__actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.plugin-card__actions :deep(.v-btn) {
  min-width: 44px;
  padding-inline: 4px;
}

.plugin-card__switch :deep(.v-switch) {
  width: 54px;
  margin-inline: 0;
}

.plugin-card__switch-wrap {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 0 0 auto;
}

.task-log-card {
  max-height: 360px;
  overflow: auto;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.task-log-card__content {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.plugin-detail-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  .plugins-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .settings-dialog-header {
    flex-direction: column;
    align-items: stretch;
    padding-bottom: 10px;
  }

  .settings-list-row__main {
    grid-template-columns: 1fr;
  }

  .settings-list-row__control {
    padding: 12px;
  }

  .plugin-card__footer {
    align-items: flex-start;
  }

  .plugin-card__footer-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .plugin-card__actions {
    width: 100%;
  }

  .plugin-card__switch {
    align-self: flex-end;
  }
}

@media (max-width: 640px) {
  .plugins-grid {
    grid-template-columns: 1fr;
  }
}
</style>
