<template>
  <v-dialog max-width="920" :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text class="d-flex flex-column ga-4">
        <v-alert density="comfortable" type="warning" variant="tonal">
          {{ restartHint }}
        </v-alert>
        <div v-if="mode === 'basic'" class="preview-list">
          <div
            v-for="item in items"
            :key="item.key"
            class="preview-item"
          >
            <div class="preview-item__key">{{ item.key }}</div>
            <div class="preview-item__values">
              <div class="preview-item__block">
                <div class="text-caption text-medium-emphasis">{{ currentLabel }}</div>
                <pre class="preview-item__code">{{ item.current }}</pre>
              </div>
              <div class="preview-item__block">
                <div class="text-caption text-medium-emphasis">{{ nextLabel }}</div>
                <pre class="preview-item__code preview-item__code--next">{{ item.next }}</pre>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="preview-raw-grid">
          <div class="preview-item__block">
            <div class="text-caption text-medium-emphasis">{{ currentLabel }}</div>
            <pre class="preview-item__code">{{ currentText }}</pre>
          </div>
          <div class="preview-item__block">
            <div class="text-caption text-medium-emphasis">{{ nextLabel }}</div>
            <pre class="preview-item__code preview-item__code--next">{{ nextText }}</pre>
          </div>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-btn variant="text" @click="emit('cancel')">{{ cancelLabel }}</v-btn>
        <v-spacer />
        <v-btn color="primary" :loading="saving" @click="emit('confirm')">
          {{ confirmLabel }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import type { SettingsPreviewItem } from './settingsEditor'

  defineProps<{
    cancelLabel: string
    confirmLabel: string
    currentLabel: string
    currentText: string
    items: SettingsPreviewItem[]
    modelValue: boolean
    mode: 'basic' | 'raw'
    nextLabel: string
    nextText: string
    restartHint: string
    saving: boolean
    title: string
  }>()

  const emit = defineEmits<{
    cancel: []
    confirm: []
    'update:modelValue': [value: boolean]
  }>()
</script>

<style scoped>
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

@media (max-width: 960px) {
  .preview-item__values,
  .preview-raw-grid {
    grid-template-columns: 1fr;
  }
}
</style>
