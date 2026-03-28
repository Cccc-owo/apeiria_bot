<template>
  <div class="raw-settings-editor">
    <div class="raw-settings-editor__toolbar">
      <div class="text-caption text-medium-emphasis">{{ description }}</div>
      <div class="raw-settings-editor__actions">
        <v-btn :loading="loading" size="small" variant="text" @click="$emit('reload')">
          {{ reloadLabel }}
        </v-btn>
        <v-btn
          color="primary"
          :disabled="!dirty || validationPending || !!validationErrorMessage"
          :loading="saving"
          size="small"
          @click="$emit('save')"
        >
          {{ saveLabel }}
        </v-btn>
      </div>
    </div>

    <v-alert v-if="activeErrorMessage" density="comfortable" type="error" variant="tonal">
      {{ activeErrorMessage }}
    </v-alert>

    <MonacoEditor
      v-model="model"
      :height="380"
      language="toml"
      :read-only="loading || saving"
      :validation-column="validationErrorColumn"
      :validation-line="validationErrorLine"
      :validation-message="validationErrorMessage"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import MonacoEditor from './MonacoEditor.vue'

  const model = defineModel<string>({ required: true })

  defineEmits<{
    reload: []
    save: []
  }>()

  const props = withDefaults(defineProps<{
    description: string
    dirty: boolean
    errorMessage: string
    loading: boolean
    reloadLabel: string
    saveLabel: string
    saving: boolean
    validationErrorColumn?: number | null
    validationErrorLine?: number | null
    validationErrorMessage?: string
    validationPending?: boolean
  }>(), {
    validationErrorColumn: null,
    validationErrorLine: null,
    validationErrorMessage: '',
    validationPending: false,
  })

  const activeErrorMessage = computed(() => props.validationErrorMessage || props.errorMessage)
</script>

<style scoped>
.raw-settings-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.raw-settings-editor__toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.raw-settings-editor__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
