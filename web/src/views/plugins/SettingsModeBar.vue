<template>
  <div class="settings-mode-bar">
    <div :aria-label="tablistLabel" class="settings-mode-tabs segmented-control" role="tablist">
      <button
        :aria-selected="modelValue === 'basic'"
        class="settings-mode-tab segmented-control__tab"
        :class="{ 'settings-mode-tab--active segmented-control__tab--active': modelValue === 'basic' }"
        role="tab"
        type="button"
        @click="$emit('update:modelValue', 'basic')"
      >
        {{ basicLabel }}
      </button>
      <button
        :aria-selected="modelValue === 'advanced'"
        class="settings-mode-tab segmented-control__tab"
        :class="{ 'settings-mode-tab--active segmented-control__tab--active': modelValue === 'advanced' }"
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
  --segmented-max-width: 320px;
}

.settings-mode-tab {
  min-width: 0;
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
