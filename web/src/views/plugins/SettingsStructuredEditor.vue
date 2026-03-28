<template>
  <div class="settings-structured-editor">
    <v-select
      v-if="schema.choices.length > 0"
      density="comfortable"
      hide-details
      item-title="title"
      item-value="value"
      :items="choiceItems"
      :model-value="modelValue"
      variant="outlined"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <v-select
      v-else-if="isNullableBoolSchema(schema)"
      density="comfortable"
      hide-details
      item-title="title"
      item-value="value"
      :items="nullableBoolItems"
      :model-value="modelValue"
      variant="outlined"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <v-switch
      v-else-if="schema.type === 'bool'"
      color="primary"
      hide-details
      inset
      :model-value="Boolean(modelValue)"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <v-text-field
      v-else-if="isScalarSchema(schema)"
      density="comfortable"
      hide-details
      :model-value="modelValue"
      :type="schema.type === 'int' || schema.type === 'float' ? 'number' : 'text'"
      variant="outlined"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <div v-else-if="isObjectSchema(schema)" class="structured-object">
      <div
        v-for="field in schema.fields"
        :key="field.key"
        class="structured-object__row"
      >
        <div class="structured-object__meta">
          <div class="structured-object__label">{{ field.key }}</div>
          <div v-if="field.help" class="structured-object__help text-caption text-medium-emphasis">
            {{ field.help }}
          </div>
        </div>
        <SettingsStructuredEditor
          :model-value="objectValue[field.key]"
          :schema="field.schema"
          @update:model-value="updateObjectField(field.key, $event)"
        />
      </div>
    </div>

    <div v-else-if="isSequenceSchema(schema)" class="structured-list">
      <div
        v-for="(item, index) in sequenceValue"
        :key="index"
        class="structured-list__item"
      >
        <div class="structured-list__item-toolbar">
          <span class="text-caption text-medium-emphasis">#{{ index + 1 }}</span>
          <v-btn
            color="warning"
            icon="mdi-delete-outline"
            size="x-small"
            variant="text"
            @click="removeSequenceItem(index)"
          />
        </div>
        <SettingsStructuredEditor
          v-if="itemSchema"
          :model-value="item"
          :schema="itemSchema.schema"
          @update:model-value="updateSequenceItem(index, $event)"
        />
      </div>
      <v-btn
        block
        color="primary"
        prepend-icon="mdi-plus"
        variant="tonal"
        @click="appendSequenceItem"
      >
        {{ t('common.add') }}
      </v-btn>
    </div>

    <div v-else-if="isMappingSchema(schema)" class="structured-map">
      <div
        v-for="(entry, index) in mappingEntries"
        :key="`${entry.key}:${index}`"
        class="structured-map__row"
      >
        <v-text-field
          class="structured-map__key"
          density="comfortable"
          hide-details
          :model-value="entry.key"
          variant="outlined"
          @update:model-value="updateMappingKey(index, String($event ?? ''))"
        />
        <SettingsStructuredEditor
          v-if="valueSchema"
          class="structured-map__value"
          :model-value="entry.value"
          :schema="valueSchema.schema"
          @update:model-value="updateMappingValue(index, $event)"
        />
        <v-btn
          color="warning"
          icon="mdi-delete-outline"
          size="small"
          variant="text"
          @click="removeMappingEntry(index)"
        />
      </div>
      <v-btn
        block
        color="primary"
        prepend-icon="mdi-plus"
        variant="tonal"
        @click="appendMappingEntry"
      >
        {{ t('common.add') }}
      </v-btn>
    </div>

    <v-textarea
      v-else
      auto-grow
      density="comfortable"
      hide-details
      :model-value="displayFieldValue(modelValue)"
      readonly
      rows="3"
      variant="outlined"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'

  import {
    buildSchemaFieldDefaultValue,
    cloneSettingValue,
    displayFieldValue,
    type PluginSettingSchema,
  } from './settingsEditor'

  defineOptions({
    name: 'SettingsStructuredEditor',
  })

  const props = defineProps<{
    modelValue: unknown
    schema: PluginSettingSchema
  }>()
  const { t } = useI18n()

  const emit = defineEmits<{
    'update:modelValue': [value: unknown]
  }>()

  const nullableBoolItems = [
    { title: 'null', value: null },
    { title: 'true', value: true },
    { title: 'false', value: false },
  ]

  const choiceItems = computed(() =>
    props.schema.choices.map(choice => ({
      title: displayFieldValue(choice),
      value: choice,
    })),
  )

  const objectValue = computed<Record<string, unknown>>(() => {
    if (props.modelValue && typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)) {
      return props.modelValue as Record<string, unknown>
    }
    return {}
  })

  const sequenceValue = computed<unknown[]>(() =>
    Array.isArray(props.modelValue) ? props.modelValue : [],
  )

  const itemSchema = computed(() => props.schema.item_schema)
  const valueSchema = computed(() => props.schema.value_schema)

  const mappingEntries = computed(() => {
    if (!props.modelValue || typeof props.modelValue !== 'object' || Array.isArray(props.modelValue)) {
      return []
    }
    return Object.entries(props.modelValue as Record<string, unknown>).map(([key, value]) => ({
      key,
      value,
    }))
  })

  function isNullableBoolSchema (schema: PluginSettingSchema) {
    return schema.type === 'bool' && schema.allows_null
  }

  function isScalarSchema (schema: PluginSettingSchema) {
    return schema.type === 'str'
      || schema.type === 'int'
      || schema.type === 'float'
      || schema.type === 'Path'
      || schema.type === 'timedelta'
      || schema.type.startsWith('IPv')
      || schema.type.startsWith('Any')
  }

  function isObjectSchema (schema: PluginSettingSchema) {
    return schema.fields.length > 0 && schema.type !== 'dict' && schema.type !== 'list' && schema.type !== 'set'
  }

  function isSequenceSchema (schema: PluginSettingSchema) {
    return (schema.type === 'list' || schema.type === 'set') && Boolean(schema.item_schema)
  }

  function isMappingSchema (schema: PluginSettingSchema) {
    return schema.type === 'dict' && Boolean(schema.value_schema)
  }

  function updateObjectField (key: string, value: unknown) {
    emit('update:modelValue', {
      ...objectValue.value,
      [key]: value,
    })
  }

  function updateSequenceItem (index: number, value: unknown) {
    const nextValue = sequenceValue.value.map((item, currentIndex) =>
      currentIndex === index ? value : cloneSettingValue(item),
    )
    emit('update:modelValue', nextValue)
  }

  function appendSequenceItem () {
    if (!itemSchema.value) return
    emit('update:modelValue', [
      ...sequenceValue.value.map(item => cloneSettingValue(item)),
      buildSchemaFieldDefaultValue(itemSchema.value),
    ])
  }

  function removeSequenceItem (index: number) {
    emit('update:modelValue', sequenceValue.value.filter((_, currentIndex) => currentIndex !== index))
  }

  function appendMappingEntry () {
    if (!valueSchema.value) return
    const nextEntries = [...mappingEntries.value]
    const nextKey = buildNextMappingKey(nextEntries.map(entry => entry.key))
    nextEntries.push({
      key: nextKey,
      value: buildSchemaFieldDefaultValue(valueSchema.value),
    })
    emit('update:modelValue', Object.fromEntries(nextEntries.map(entry => [entry.key, entry.value])))
  }

  function updateMappingKey (index: number, value: string) {
    const nextEntries = mappingEntries.value.map((entry, currentIndex) =>
      currentIndex === index ? { ...entry, key: value } : { ...entry, value: cloneSettingValue(entry.value) },
    )
    emit('update:modelValue', Object.fromEntries(nextEntries.map(entry => [entry.key, entry.value])))
  }

  function updateMappingValue (index: number, value: unknown) {
    const nextEntries = mappingEntries.value.map((entry, currentIndex) =>
      currentIndex === index ? { ...entry, value } : { ...entry, value: cloneSettingValue(entry.value) },
    )
    emit('update:modelValue', Object.fromEntries(nextEntries.map(entry => [entry.key, entry.value])))
  }

  function removeMappingEntry (index: number) {
    const nextEntries = mappingEntries.value.filter((_, currentIndex) => currentIndex !== index)
    emit('update:modelValue', Object.fromEntries(nextEntries.map(entry => [entry.key, entry.value])))
  }

  function buildNextMappingKey (existingKeys: string[]) {
    const usedKeys = new Set(existingKeys)
    if (!usedKeys.has('key_1')) return 'key_1'
    let index = 2
    while (usedKeys.has(`key_${index}`)) {
      index += 1
    }
    return `key_${index}`
  }
</script>

<style scoped>
.settings-structured-editor {
  width: 100%;
}

.structured-object,
.structured-list,
.structured-map {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.structured-object__row,
.structured-list__item,
.structured-map__row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(var(--v-border-color), 0.65);
  background: rgba(var(--v-theme-on-surface), 0.018);
}

.structured-object__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.structured-object__label {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
}

.structured-object__help {
  line-height: 1.4;
}

.structured-list__item-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.structured-map__key {
  flex: 0 0 auto;
}

.structured-map__value {
  flex: 1 1 auto;
}

@media (min-width: 720px) {
  .structured-map__row {
    display: grid;
    grid-template-columns: minmax(160px, 220px) minmax(0, 1fr) auto;
    align-items: start;
  }
}
</style>
