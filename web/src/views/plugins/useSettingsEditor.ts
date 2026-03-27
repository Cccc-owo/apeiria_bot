import { computed, ref } from 'vue'

import { getErrorMessage } from '@/api/client'
import { useNoticeStore } from '@/stores/notice'

import {
  buildChangedValues,
  buildFieldFormValue,
  buildOverrideInitialValue,
  buildSettingsForm,
  hasPendingChanges,
  type PluginSettingField,
  type PluginSettingsState,
} from './settingsEditor'

interface SettingsEditorMessages {
  clearSuccess: string
  invalidJson: string
  loadFailed: string
  saveFailed: string
  saveSuccess: string
}

interface SettingsEditorResponse {
  data: PluginSettingsState
}

interface UseSettingsEditorOptions {
  clear: (key: string) => Promise<SettingsEditorResponse>
  load?: () => Promise<SettingsEditorResponse>
  messages: SettingsEditorMessages
  save: (values: Record<string, unknown>) => Promise<SettingsEditorResponse>
}

export function useSettingsEditor (options: UseSettingsEditorOptions) {
  const noticeStore = useNoticeStore()
  const loading = ref(false)
  const saving = ref(false)
  const clearingKey = ref('')
  const errorMessage = ref('')
  const state = ref<PluginSettingsState | null>(null)
  const form = ref<Record<string, unknown>>({})
  const draftOverrides = ref<Record<string, boolean>>({})

  const fields = computed(() => state.value?.fields ?? [])
  const hasPendingChangesState = computed(() =>
    hasPendingChanges(
      fields.value.filter(field => isFieldEditing(field)),
      form.value,
      options.messages.invalidJson,
    ),
  )

  function applyState (nextState: PluginSettingsState) {
    state.value = nextState
    form.value = buildSettingsForm(nextState.fields)
    draftOverrides.value = {}
  }

  function reset () {
    errorMessage.value = ''
    state.value = null
    form.value = {}
    draftOverrides.value = {}
  }

  function isFieldEditing (field: PluginSettingField) {
    return field.has_local_override || Boolean(draftOverrides.value[field.key])
  }

  function startOverride (field: PluginSettingField) {
    draftOverrides.value = {
      ...draftOverrides.value,
      [field.key]: true,
    }
    form.value[field.key] = buildOverrideInitialValue(field)
  }

  async function reload () {
    if (!options.load) return
    loading.value = true
    errorMessage.value = ''
    try {
      const response = await options.load()
      applyState(response.data)
    } catch (error) {
      errorMessage.value = getErrorMessage(error, options.messages.loadFailed)
    } finally {
      loading.value = false
    }
  }

  async function submit () {
    const editingFields = fields.value.filter(field => isFieldEditing(field))
    let values: Record<string, unknown> = {}
    try {
      values = buildChangedValues(editingFields, form.value, options.messages.invalidJson)
    } catch (error) {
      const message = getErrorMessage(error, options.messages.invalidJson)
      errorMessage.value = message
      noticeStore.show(message, 'error')
      return
    }

    if (Object.keys(values).length === 0) return

    saving.value = true
    errorMessage.value = ''
    try {
      const response = await options.save(values)
      applyState(response.data)
      noticeStore.show(options.messages.saveSuccess, 'success')
    } catch (error) {
      const message = getErrorMessage(error, options.messages.saveFailed)
      errorMessage.value = message
      noticeStore.show(message, 'error')
    } finally {
      saving.value = false
    }
  }

  async function clearField (field: PluginSettingField) {
    clearingKey.value = field.key
    errorMessage.value = ''
    try {
      const response = await options.clear(field.key)
      applyState(response.data)
      noticeStore.show(options.messages.clearSuccess, 'success')
    } catch (error) {
      const message = getErrorMessage(error, options.messages.saveFailed)
      errorMessage.value = message
      noticeStore.show(message, 'error')
    } finally {
      clearingKey.value = ''
    }
  }

  function cancelField (field: PluginSettingField) {
    const nextDraftOverrides = { ...draftOverrides.value }
    delete nextDraftOverrides[field.key]
    draftOverrides.value = nextDraftOverrides
    form.value[field.key] = buildFieldFormValue(field)
    errorMessage.value = ''
  }

  return {
    applyState,
    cancelField,
    clearField,
    clearingKey,
    draftOverrides,
    errorMessage,
    fields,
    form,
    hasPendingChanges: hasPendingChangesState,
    isFieldEditing,
    loading,
    reload,
    reset,
    saving,
    startOverride,
    state,
    submit,
  }
}
