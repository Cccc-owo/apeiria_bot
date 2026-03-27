<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('plugins.title') }}</h1>
      <div class="page-actions">
        <v-btn :loading="loading" variant="tonal" @click="loadPlugins">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
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
                      <div class="settings-list-row__info">
                        <div class="settings-list-row__title">
                          <span class="font-weight-medium">{{ field.key }}</span>
                          <v-chip
                            :color="field.has_local_override ? 'primary' : 'default'"
                            size="x-small"
                            variant="tonal"
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
                            color="primary"
                            size="small"
                            variant="text"
                            @click="coreEditor.startOverride(field)"
                          >
                            {{ t('plugins.settingsAddOverride') }}
                          </v-btn>
                          <v-btn
                            v-if="field.has_local_override"
                            color="warning"
                            :loading="coreClearingKey === field.key"
                            size="small"
                            variant="text"
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
                        :array-hint="t('plugins.settingsArrayHint')"
                        :editing="coreEditor.isFieldEditing(field)"
                        :field="field"
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
                  @save="openCoreRawPreview"
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
                      color="primary"
                      size="small"
                      variant="text"
                      @click="pluginEditor.startOverride(field)"
                    >
                      {{ t('plugins.settingsAddOverride') }}
                    </v-btn>
                    <v-btn
                      v-if="field.has_local_override"
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
            <div
              class="confirm-plugin-item"
            >
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
    type DriverConfigItem,
    getAdapterConfig,
    getCoreSettings,
    getCoreSettingsRaw,
    getDriverConfig,
    getPluginConfig,
    getPlugins,
    getPluginSettings,
    getPluginSettingsRaw,
    type ModuleConfigItem,
    type PluginItem,
    type RawSettingsResponse,
    updateCoreSettings,
    updateCoreSettingsRaw,
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
  const sectionTab = ref('plugins')
  const hideSystemPlugins = ref(true)
  const pluginSearch = ref('')
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
  const settingsPlugin = ref<PluginItem | null>(null)
  const settingsEditorMode = ref<'basic' | 'advanced'>('basic')
  const settingsRawText = ref('')
  const settingsRawInitialText = ref('')
  const settingsRawLoading = ref(false)
  const settingsRawSaving = ref(false)
  const settingsRawErrorMessage = ref('')
  const previewDialogVisible = ref(false)
  const previewMode = ref<'basic' | 'raw'>('basic')
  const previewAction = ref<'plugin-basic' | 'plugin-raw' | 'core-basic' | 'core-raw'>('plugin-basic')
  const toggleConfirmVisible = ref(false)
  const toggleConfirmLoading = ref(false)
  const toggleConfirmItem = ref<PluginItem | null>(null)
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
  const settingsForm = pluginEditor.form
  const coreLoading = coreEditor.loading
  const coreSaving = coreEditor.saving
  const coreClearingKey = coreEditor.clearingKey
  const coreErrorMessage = coreEditor.errorMessage
  const coreSettings = coreEditor.state
  const coreForm = coreEditor.form
  const hasPendingCoreRawChanges = computed(() => coreRawText.value !== coreRawInitialText.value)
  const hasPendingPluginRawChanges = computed(() => settingsRawText.value !== settingsRawInitialText.value)

  function normalizeConfigEntry (value: string) {
    const normalized = value.trim()
    if (!normalized) return ''
    if (['none', 'null'].includes(normalized.toLowerCase())) return ''
    return normalized
  }

  function normalizeConfigEntries (values: string[]) {
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

  function applyRouteFilters () {
    const sectionQuery = route.query.section
    if (
      sectionQuery === 'core'
      || sectionQuery === 'plugins'
      || sectionQuery === 'adapters'
      || sectionQuery === 'drivers'
    ) {
      sectionTab.value = sectionQuery
    }
    const searchQuery = route.query.search
    pluginSearch.value = typeof searchQuery === 'string' ? searchQuery : ''
  }
  const previewSaving = computed(() =>
    settingsSaving.value || settingsRawSaving.value || coreSaving.value || coreRawSaving.value,
  )
  const previewTitle = computed(() =>
    previewMode.value === 'basic' ? t('plugins.previewChangesTitle') : t('plugins.previewRawTitle'),
  )
  const toggleConfirmTitle = computed(() =>
    t('plugins.disableConfirmTitle'),
  )
  const toggleConfirmSummary = computed(() => {
    if (!toggleConfirmItem.value) return ''
    const riskCount = toggleConfirmItem.value.dependent_plugins.length
    if (riskCount > 0) {
      return t('plugins.disableConfirmRiskSummary', { count: 1, riskCount })
    }
    return t('plugins.disableConfirmSummary', { count: 1 })
  })

  const SOURCE_COLORS: Record<string, string> = {
    framework: 'error',
    official: 'primary',
    custom: 'success',
    builtin: 'secondary',
    external: 'warning',
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

  const hasPendingCoreChanges = coreEditor.hasPendingChanges
  const hasPendingPluginChanges = pluginEditor.hasPendingChanges
  const previewItems = computed(() => {
    if (previewAction.value === 'plugin-basic') {
      return buildPreviewItems(settingsFields.value, settingsForm.value, pluginEditor.draftOverrides.value)
    }
    return buildPreviewItems(coreFields.value, coreForm.value, coreEditor.draftOverrides.value)
  })
  const previewCurrentText = computed(() =>
    previewAction.value === 'plugin-raw' ? settingsRawInitialText.value : coreRawInitialText.value,
  )
  const previewNextText = computed(() =>
    previewAction.value === 'plugin-raw' ? settingsRawText.value : coreRawText.value,
  )

  function applyCoreRawState (nextState: RawSettingsResponse) {
    coreRawText.value = nextState.text
    coreRawInitialText.value = nextState.text
  }

  function applyPluginRawState (nextState: RawSettingsResponse) {
    settingsRawText.value = nextState.text
    settingsRawInitialText.value = nextState.text
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

  async function loadPlugins () {
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

  async function saveCoreSettings () {
    if (!coreSettings.value) return
    await coreEditor.submit()
  }

  function openCoreSettingsPreview () {
    if (!coreSettings.value) return
    const items = buildPreviewItems(coreFields.value, coreForm.value, coreEditor.draftOverrides.value)
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

  async function clearCoreField (field: PluginSettingField) {
    await coreEditor.clearField(field)
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
    } else if (previewAction.value === 'plugin-raw') {
      await savePluginRawSettings()
    } else if (previewAction.value === 'core-basic') {
      await saveCoreSettings()
    } else {
      await saveCoreRawSettings()
    }

    if (
      !settingsErrorMessage.value
      && !settingsRawErrorMessage.value
      && !coreErrorMessage.value
      && !coreRawErrorMessage.value
    ) {
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

  function driverChipColor (item: DriverConfigItem) {
    return item.is_active ? 'success' : 'warning'
  }

  function driverStatusText (item: DriverConfigItem) {
    return item.is_active ? t('plugins.driverActive') : t('plugins.driverRegisteredOnly')
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
    void loadPlugins()
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
  min-width: 0;
}

.plugin-status-card__actions {
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
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

@media (max-width: 960px) {
  .plugin-status-card__toolbar {
    justify-content: flex-end;
  }
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
  gap: 4px;
  padding: 4px 0;
}

.plugins-table__title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.plugins-table__description {
  line-height: 1.35;
}

.plugins-table__meta {
  line-height: 1.3;
}

.plugins-table__relations {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
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

.plugin-detail-meta {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.plugin-detail-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
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

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(var(--v-theme-on-surface), 0.03);
}

.preview-item__key {
  font-weight: 700;
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
  gap: 6px;
  min-width: 0;
}

.preview-item__code {
  margin: 0;
  min-height: 72px;
  padding: 12px;
  border-radius: 12px;
  background: rgb(var(--v-theme-surface-container-low));
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.83rem;
  line-height: 1.4;
}

.preview-item__code--next {
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.24);
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
  background: rgb(var(--v-theme-surface-container-low));
}

.confirm-plugin-item__title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.confirm-plugin-item__relations {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
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

  .section-heading__actions {
    width: 100%;
  }

  .plugin-search {
    width: 100%;
  }

  .preview-item__values,
  .preview-raw-grid {
    grid-template-columns: 1fr;
  }
}
</style>
