export interface PluginSettingField {
  key: string
  type: string
  editor: string
  item_type: string | null
  key_type: string | null
  default: unknown
  help: string
  choices: unknown[]
  current_value: unknown
  local_value: unknown
  value_source: string
  global_key: string | null
  has_local_override: boolean
  allows_null: boolean
  editable: boolean
  type_category: string
}

export interface PluginSettingsState {
  module_name: string
  section: string
  legacy_flatten: boolean
  config_source: string
  has_config_model: boolean
  fields: PluginSettingField[]
}

export function displayFieldValue(value: unknown) {
  if (value == null) return 'null'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

export function isSequenceChipField(field: PluginSettingField) {
  return field.editor === 'chips'
}

export function isTextInputField(field: PluginSettingField) {
  return field.editor === 'input'
}

export function textInputType(field: PluginSettingField) {
  return field.type === 'int' || field.type === 'float' ? 'number' : 'text'
}

export function isNullableBoolField(field: PluginSettingField) {
  return field.type === 'bool' && field.allows_null
}

export function toEditorValue(field: PluginSettingField, sourceValue: unknown) {
  if (sourceValue == null && field.allows_null) {
    return null
  }
  if (field.type === 'bool') {
    return typeof sourceValue === 'boolean' ? sourceValue : false
  }
  if (field.type === 'int' || field.type === 'float') {
    return sourceValue ?? ''
  }
  if (field.type_category === 'sequence') {
    const value = Array.isArray(sourceValue) ? [...sourceValue] : []
    return isSequenceChipField(field) ? value : JSON.stringify(value, null, 2)
  }
  if (field.type_category === 'mapping') {
    return JSON.stringify(sourceValue ?? {}, null, 2)
  }
  return sourceValue ?? ''
}

export function buildSettingsForm(fields: PluginSettingField[]) {
  const next: Record<string, unknown> = {}
  for (const field of fields) {
    const sourceValue = field.has_local_override ? field.local_value : null
    next[field.key] = toEditorValue(field, sourceValue)
  }
  return next
}

export function buildOverrideInitialValue(field: PluginSettingField) {
  return toEditorValue(field, field.current_value ?? field.default)
}

function coercePrimitiveValue(typeName: string | null, value: unknown) {
  if (typeName === 'int') {
    if (typeof value !== 'number' || !Number.isInteger(value)) {
      throw new Error('invalid int')
    }
    return value
  }
  if (typeName === 'float') {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new Error('invalid float')
    }
    return value
  }
  if (typeName === 'bool') {
    if (typeof value === 'boolean') return value
    throw new Error('invalid bool')
  }
  if (value == null) return null
  return String(value)
}

function normalizeScalarNumberValue(
  typeName: 'int' | 'float',
  rawValue: unknown,
) {
  if (rawValue === null) return null
  const numericValue =
    typeof rawValue === 'number'
      ? rawValue
      : typeof rawValue === 'string' && rawValue.trim()
        ? Number(rawValue)
        : Number.NaN

  if (typeName === 'int') {
    if (!Number.isInteger(numericValue)) {
      throw new Error('invalid int')
    }
    return numericValue
  }
  if (!Number.isFinite(numericValue)) {
    throw new Error('invalid float')
  }
  return numericValue
}

function normalizeSequenceValue(field: PluginSettingField, rawValue: unknown) {
  if (rawValue == null && field.allows_null) {
    return null
  }
  let values: unknown[] = []
  if (isSequenceChipField(field)) {
    values = Array.isArray(rawValue) ? rawValue : []
  } else {
    if (typeof rawValue !== 'string' || !rawValue.trim()) return null
    const parsed = JSON.parse(rawValue)
    if (!Array.isArray(parsed)) throw new Error('invalid array')
    values = parsed
  }
  return values
    .map((item) => coercePrimitiveValue(field.item_type, item))
    .filter((item) => item !== '')
}

export function normalizeFieldValueForSave(
  field: PluginSettingField,
  rawValue: unknown,
) {
  if ((field.type === 'int' || field.type === 'float') && rawValue === '') {
    return null
  }
  if (field.type === 'int') {
    return normalizeScalarNumberValue('int', rawValue)
  }
  if (field.type === 'float') {
    return normalizeScalarNumberValue('float', rawValue)
  }
  if (field.type_category === 'sequence') {
    return normalizeSequenceValue(field, rawValue)
  }
  if (field.type_category === 'mapping') {
    if (typeof rawValue !== 'string' || !rawValue.trim()) return null
    return JSON.parse(rawValue)
  }
  if (
    field.type_category === 'path'
    || field.type_category === 'duration'
    || field.type_category === 'text_like'
  ) {
    return rawValue === null ? null : String(rawValue)
  }
  return rawValue
}

export function normalizeComparableFieldValue(
  field: PluginSettingField,
  value: unknown,
) {
  if (value == null) return null
  if (field.type === 'float') return Number(value)
  if (field.type_category === 'sequence') {
    return Array.isArray(value)
      ? value.map((item) => field.item_type === 'float' ? Number(item) : item)
      : []
  }
  return value
}

export function resolveNullableFieldValue(
  field: PluginSettingField,
  value: unknown,
) {
  if (value !== null || field.allows_null) return value
  throw new Error('null not allowed')
}

function isSameSettingValue(left: unknown, right: unknown) {
  return JSON.stringify(left) === JSON.stringify(right)
}

export function buildChangedValues(
  fields: PluginSettingField[],
  form: Record<string, unknown>,
  invalidJsonMessage: string,
) {
  const values: Record<string, unknown> = {}
  for (const field of fields) {
    if (!field.editable) continue
    let value = form[field.key]
    try {
      value = normalizeFieldValueForSave(field, value)
    } catch (error) {
      const message = error instanceof Error ? error.message : invalidJsonMessage
      throw new Error(`${field.key}: ${message}`)
    }
    value = resolveNullableFieldValue(field, value)
    const currentValue = normalizeComparableFieldValue(field, field.current_value)
    if (!isSameSettingValue(value, currentValue)) {
      values[field.key] = value
    }
  }
  return values
}

export function hasPendingChanges(
  fields: PluginSettingField[],
  form: Record<string, unknown>,
  invalidJsonMessage: string,
) {
  try {
    return Object.keys(buildChangedValues(fields, form, invalidJsonMessage)).length > 0
  } catch {
    return fields.length > 0
  }
}
