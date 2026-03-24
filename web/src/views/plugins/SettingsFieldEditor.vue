<template>
  <v-switch
    v-if="editing && field.editable && field.editor === 'switch' && !isNullableBoolField(field)"
    :model-value="modelValue"
    color="primary"
    hide-details
    inset
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-select
    v-else-if="editing && field.editable && isNullableBoolField(field)"
    :model-value="modelValue"
    :items="nullableBoolItems"
    item-title="title"
    item-value="value"
    variant="outlined"
    density="comfortable"
    hide-details
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-select
    v-else-if="editing && field.editable && field.editor === 'select'"
    :model-value="modelValue"
    :items="field.choices"
    variant="outlined"
    density="comfortable"
    hide-details
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-text-field
    v-else-if="editing && field.editable && isTextInputField(field)"
    :model-value="modelValue"
    :type="textInputType(field)"
    variant="outlined"
    density="comfortable"
    hide-details
    :placeholder="displayFieldValue(field.current_value)"
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-combobox
    v-else-if="editing && field.editable && isSequenceChipField(field)"
    :model-value="modelValue"
    variant="outlined"
    chips
    closable-chips
    multiple
    density="comfortable"
    hide-details
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-textarea
    v-else-if="editing && field.editable && field.editor === 'json_array'"
    :model-value="modelValue"
    variant="outlined"
    auto-grow
    rows="4"
    density="comfortable"
    :hint="arrayHint"
    persistent-hint
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-textarea
    v-else-if="editing && field.editable && field.editor === 'json_object'"
    :model-value="modelValue"
    variant="outlined"
    auto-grow
    rows="4"
    density="comfortable"
    :hint="jsonHint"
    persistent-hint
    @update:model-value="emit('update:modelValue', $event)"
  />

  <v-textarea
    v-else-if="showReadonly"
    :model-value="displayFieldValue(field.current_value)"
    variant="outlined"
    readonly
    auto-grow
    :rows="readonlyRows"
    density="comfortable"
    hide-details
  />
</template>

<script setup lang="ts">
import {
  displayFieldValue,
  isNullableBoolField,
  isSequenceChipField,
  isTextInputField,
  textInputType,
  type PluginSettingField,
} from './settingsEditor'

withDefaults(defineProps<{
  arrayHint: string
  editing: boolean
  field: PluginSettingField
  jsonHint: string
  modelValue: unknown
  readonlyRows?: number
  showReadonly?: boolean
}>(), {
  readonlyRows: 2,
  showReadonly: true,
})

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
}>()

const nullableBoolItems = [
  { title: 'null', value: null },
  { title: 'true', value: true },
  { title: 'false', value: false },
]
</script>
