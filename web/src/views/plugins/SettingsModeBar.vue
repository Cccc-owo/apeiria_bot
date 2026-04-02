<template>
  <div class="settings-mode-bar">
    <v-btn-toggle
      :aria-label="tablistLabel"
      class="settings-mode-tabs"
      density="comfortable"
      mandatory
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
    >
      <v-btn
        class="settings-mode-tab"
        rounded="pill"
        value="basic"
        variant="text"
      >
        {{ basicLabel }}
      </v-btn>
      <v-btn
        class="settings-mode-tab"
        rounded="pill"
        value="advanced"
        variant="text"
      >
        {{ advancedLabel }}
      </v-btn>
    </v-btn-toggle>

    <div v-if="$slots.actions" class="settings-mode-bar__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
  defineProps<{
    advancedLabel: string
    basicLabel: string
    modelValue: 'basic' | 'advanced'
    tablistLabel: string
  }>()

  defineEmits<{
    'update:modelValue': [value: 'basic' | 'advanced']
  }>()
</script>

<style scoped>
.settings-mode-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.settings-mode-tabs {
  --segmented-max-width: 320px;
  width: min(320px, 100%);
  border-radius: var(--shape-pill);
  background: rgba(var(--v-theme-surface-container-high), 0.9);
  border: 1px solid rgba(var(--v-theme-outline), 0.24);
  padding: 4px;
}

.settings-mode-tab {
  min-width: 0 !important;
  text-transform: none !important;
}

.settings-mode-tabs :deep(.v-btn--active) {
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
}

.settings-mode-bar__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 0 auto;
}

@media (max-width: 600px) {
  .settings-mode-bar {
    align-items: stretch;
  }

  .settings-mode-tabs {
    width: 100%;
  }

  .settings-mode-bar__actions {
    justify-content: flex-start;
  }
}
</style>
