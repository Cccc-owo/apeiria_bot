<template>
  <div class="d-flex flex-column ga-6">
    <div class="d-flex align-center flex-wrap ga-3">
      <h1 class="text-h4">{{ t('data.title') }}</h1>
      <v-spacer />
      <v-select
        v-model="selectedTable"
        :items="tableOptions"
        item-title="label"
        item-value="name"
        :label="t('data.table')"
        variant="outlined"
        density="comfortable"
        hide-details
        class="data-table-select"
      />
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <v-card>
      <v-card-text class="d-flex align-center flex-wrap ga-4">
        <div>
          <div class="text-caption text-medium-emphasis">{{ t('data.currentTable') }}</div>
          <div class="text-subtitle-1">{{ selectedTableLabel || t('data.notSelected') }}</div>
        </div>
        <div>
          <div class="text-caption text-medium-emphasis">{{ t('data.total') }}</div>
          <div class="text-subtitle-1">{{ total }}</div>
        </div>
        <div>
          <div class="text-caption text-medium-emphasis">{{ t('data.pageSize') }}</div>
          <div class="text-subtitle-1">{{ pageSize }}</div>
        </div>
      </v-card-text>
    </v-card>

    <v-card>
      <v-data-table-server
        v-model:items-per-page="pageSize"
        v-model:page="page"
        :headers="headers"
        :items="rows"
        :items-length="total"
        :loading="loading"
        density="comfortable"
        :loading-text="t('data.loadingText')"
        :items-per-page-text="t('data.itemsPerPage')"
        @update:options="handleOptionsChange"
      >
        <template #item.actions="{ item }">
          <v-btn
            size="small"
            variant="text"
            color="primary"
            @click="openRecordDialog(item)"
          >
            {{ t('data.viewEdit') }}
          </v-btn>
        </template>
        <template #item="{ item, columns }">
          <tr>
            <td
              v-for="column in columns"
              :key="String(column.key)"
              class="data-cell"
            >
              <template v-if="String(column.key) === 'actions'">
                <v-btn
                  size="small"
                  variant="text"
                  color="primary"
                  @click="openRecordDialog(item)"
                >
                  {{ t('data.viewEdit') }}
                </v-btn>
              </template>
              <template v-else>
                {{ formatCell(item[String(column.key) as keyof typeof item]) }}
              </template>
            </td>
          </tr>
        </template>
      </v-data-table-server>
    </v-card>

    <v-dialog v-model="recordDialogVisible" max-width="840">
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>{{ t('data.detail') }}</span>
          <v-spacer />
          <v-chip v-if="editingRecordId" size="small" variant="tonal">
            {{ selectedTableLabel }} #{{ editingRecordId }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <v-alert
            v-if="dialogErrorMessage"
            type="error"
            variant="tonal"
            density="comfortable"
            class="mb-4"
          >
            {{ dialogErrorMessage }}
          </v-alert>

          <div v-if="dialogLoading" class="py-8 d-flex justify-center">
            <v-progress-circular indeterminate color="primary" />
          </div>

          <div v-else class="d-flex flex-column ga-4">
            <template v-for="field in editableFields" :key="field">
              <v-switch
                v-if="fieldType(field) === 'boolean'"
                v-model="booleanEditForm[field]"
                :label="field"
                color="primary"
                hide-details
                inset
                :readonly="!isEditableField(field)"
              />
              <v-text-field
                v-else-if="fieldType(field) === 'number'"
                v-model="editForm[field]"
                :label="field"
                variant="outlined"
                density="comfortable"
                type="number"
                :readonly="!isEditableField(field)"
              />
              <v-textarea
                v-else-if="fieldType(field) === 'json'"
                v-model="editForm[field]"
                :label="field"
                variant="outlined"
                density="comfortable"
                auto-grow
                rows="4"
                :readonly="!isEditableField(field)"
              />
              <v-text-field
                v-else
                v-model="editForm[field]"
                :label="field"
                variant="outlined"
                density="comfortable"
                :readonly="!isEditableField(field)"
              />
            </template>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="recordDialogVisible = false">{{ t('common.close') }}</v-btn>
          <v-spacer />
          <v-btn
            color="primary"
            :loading="savingRecord"
            :disabled="!editingRecordId"
            @click="saveRecord"
          >
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDataRecord, getDataRecords, getDataTables, updateDataRecord } from '@/api'
import { useNoticeStore } from '@/stores/notice'

interface DataTableInfo {
  name: string
  label: string
  primary_key: string
}

const tables = ref<DataTableInfo[]>([])
const selectedTable = ref('')
const primaryKey = ref('id')
const headers = ref<{ title: string; key: string; sortable: boolean }[]>([])
const rows = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const errorMessage = ref('')
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const recordDialogVisible = ref(false)
const dialogLoading = ref(false)
const savingRecord = ref(false)
const dialogErrorMessage = ref('')
const editingRecordId = ref('')
const originalRecord = ref<Record<string, unknown>>({})
const editForm = ref<Record<string, string>>({})
const booleanEditForm = ref<Record<string, boolean>>({})
const noticeStore = useNoticeStore()
const { t } = useI18n()

const tableOptions = computed(() => tables.value)
const selectedTableLabel = computed(
  () => tables.value.find((item) => item.name === selectedTable.value)?.label || '',
)
const editableFields = computed(() => Object.keys(editForm.value))

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function isEditableField(field: string) {
  return ![primaryKey.value, 'created_at', 'updated_at'].includes(field)
}

function fieldType(field: string) {
  const original = originalRecord.value[field]
  if (typeof original === 'boolean') return 'boolean'
  if (typeof original === 'number') return 'number'
  if (original && typeof original === 'object') return 'json'
  return 'text'
}

function stringifyValue(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function normalizeEditedValue(field: string, rawValue: string) {
  const original = originalRecord.value[field]

  if (!isEditableField(field)) {
    return original
  }
  if (rawValue === '' && original === null) {
    return null
  }
  if (typeof original === 'number') {
    const parsed = Number(rawValue)
    return Number.isNaN(parsed) ? original : parsed
  }
  if (typeof original === 'boolean') {
    return rawValue === 'true'
  }
  if (original && typeof original === 'object') {
    try {
      return JSON.parse(rawValue)
    } catch {
      return original
    }
  }
  return rawValue
}

async function loadTables() {
  const response = await getDataTables()
  tables.value = response.data
  if (!selectedTable.value && tables.value.length > 0) {
    selectedTable.value = tables.value[0].name
  }
}

async function loadRecords() {
  if (!selectedTable.value) return

  loading.value = true
  errorMessage.value = ''
  try {
    const response = await getDataRecords(selectedTable.value, page.value, pageSize.value)
    primaryKey.value = response.data.primary_key
    headers.value = [
      ...response.data.columns.map((column) => ({
        title: column,
        key: column,
        sortable: false,
      })),
      { title: t('data.actions'), key: 'actions', sortable: false },
    ]
    rows.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('data.loadFailed')
  } finally {
    loading.value = false
  }
}

async function openRecordDialog(row: Record<string, unknown>) {
  const recordId = row[primaryKey.value]
  if (recordId === null || recordId === undefined) {
    return
  }

  recordDialogVisible.value = true
  dialogLoading.value = true
  dialogErrorMessage.value = ''
  editingRecordId.value = String(recordId)
  try {
    const response = await getDataRecord(selectedTable.value, editingRecordId.value)
    originalRecord.value = response.data.record
    editForm.value = Object.fromEntries(
      Object.entries(response.data.record).map(([key, value]) => [key, stringifyValue(value)]),
    )
    booleanEditForm.value = Object.fromEntries(
      Object.entries(response.data.record)
        .filter(([, value]) => typeof value === 'boolean')
        .map(([key, value]) => [key, Boolean(value)]),
    )
  } catch (error) {
    dialogErrorMessage.value = error instanceof Error ? error.message : t('data.loadRecordFailed')
  } finally {
    dialogLoading.value = false
  }
}

async function saveRecord() {
  if (!editingRecordId.value) return

  savingRecord.value = true
  dialogErrorMessage.value = ''
  try {
    const values = Object.fromEntries(
      Object.entries(editForm.value)
        .filter(([field]) => isEditableField(field))
        .map(([field, rawValue]) => {
          if (fieldType(field) === 'boolean') {
            return [field, booleanEditForm.value[field] ?? false]
          }
          return [field, normalizeEditedValue(field, rawValue)]
        }),
    )

    const response = await updateDataRecord(selectedTable.value, editingRecordId.value, values)
    originalRecord.value = response.data.record
    editForm.value = Object.fromEntries(
      Object.entries(response.data.record).map(([key, value]) => [key, stringifyValue(value)]),
    )
    booleanEditForm.value = Object.fromEntries(
      Object.entries(response.data.record)
        .filter(([, value]) => typeof value === 'boolean')
        .map(([key, value]) => [key, Boolean(value)]),
    )
    recordDialogVisible.value = false
    await loadRecords()
    noticeStore.show(t('data.updated'), 'success')
  } catch (error) {
    dialogErrorMessage.value = error instanceof Error ? error.message : t('data.saveFailed')
    noticeStore.show(dialogErrorMessage.value, 'error')
  } finally {
    savingRecord.value = false
  }
}

function handleOptionsChange(options: { page: number; itemsPerPage: number }) {
  if (page.value !== options.page) {
    page.value = options.page
  }
  if (pageSize.value !== options.itemsPerPage) {
    pageSize.value = options.itemsPerPage
  }
}

watch(selectedTable, () => {
  page.value = 1
  headers.value = []
  rows.value = []
  total.value = 0
  void loadRecords()
})

watch([page, pageSize], () => {
  void loadRecords()
})

onMounted(async () => {
  await loadTables()
})
</script>

<style scoped>
.data-table-select {
  max-width: 240px;
  min-width: 220px;
}

.data-cell {
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
