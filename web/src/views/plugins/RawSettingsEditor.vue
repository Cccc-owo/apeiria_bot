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
          :disabled="!dirty"
          :loading="saving"
          size="small"
          @click="$emit('save')"
        >
          {{ saveLabel }}
        </v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
      {{ errorMessage }}
    </v-alert>

    <MonacoEditor
      v-model="model"
      :height="380"
      language="toml"
      :read-only="loading || saving"
    />
  </div>
</template>

<script setup lang="ts">
  import MonacoEditor from './MonacoEditor.vue'

  const model = defineModel<string>({ required: true })

  defineProps<{
    description: string
    dirty: boolean
    errorMessage: string
    loading: boolean
    reloadLabel: string
    saveLabel: string
    saving: boolean
  }>()

  defineEmits<{
    reload: []
    save: []
  }>()
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
