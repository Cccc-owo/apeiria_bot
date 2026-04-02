<template>
  <div class="settings-mode-bar">
    <div :aria-label="tablistLabel" class="settings-mode-tabs" role="tablist">
      <button
        :aria-selected="modelValue === 'basic'"
        class="settings-mode-tab"
        :class="{ 'settings-mode-tab--active': modelValue === 'basic' }"
        role="tab"
        type="button"
        @click="$emit('update:modelValue', 'basic')"
      >
        {{ basicLabel }}
      </button>
      <button
        :aria-selected="modelValue === 'advanced'"
        class="settings-mode-tab"
        :class="{ 'settings-mode-tab--active': modelValue === 'advanced' }"
        role="tab"
        type="button"
        @click="$emit('update:modelValue', 'advanced')"
      >
        {{ advancedLabel }}
      </button>
    </div>

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
  display: inline-flex;
  align-items: stretch;
  width: min(320px, 100%);
  min-width: 0;
  padding: 4px;
  border-radius: var(--shape-base);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgba(var(--v-theme-surface-variant), 0.22);
}

.settings-mode-tab {
  flex: 1 1 0;
  min-width: 0;
  height: 40px;
  border: 0;
  border-radius: var(--shape-small);
  background: transparent;
  color: rgba(var(--v-theme-on-surface), 0.72);
  font-size: 0.95rem;
  font-weight: 600;
  transition:
    background-color 0.16s ease,
    color 0.16s ease,
    box-shadow 0.16s ease;
}

.settings-mode-tab:hover {
  color: rgb(var(--v-theme-on-surface));
}

.settings-mode-tab--active {
  background: rgba(var(--v-theme-primary), 0.18);
  color: rgb(var(--v-theme-primary));
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.14);
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
