<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('data.title') }}</h1>
      <v-spacer />
      <div class="page-toolbar-form">
        <v-btn variant="tonal" :loading="loading" @click="loadRecords">
          {{ t('common.refresh') }}
        </v-btn>
        <div class="compact-field compact-field--toolbar data-table-select">
          <label class="compact-field__label" for="data-table-select">{{ t('data.table') }}</label>
          <v-select
            id="data-table-select"
            v-model="selectedTable"
            :items="tableOptions"
            item-title="label"
            item-value="name"
            hide-details
          />
        </div>
      </div>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <div class="page-summary-grid">
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('data.currentTable') }}</div>
        <div class="summary-card__value summary-card__value--text">{{ selectedTableLabel || t('data.notSelected') }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('data.total') }}</div>
        <div class="summary-card__value">{{ total }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('data.pageSize') }}</div>
        <div class="summary-card__value">{{ pageSize }}</div>
      </v-sheet>
    </div>

    <v-card class="page-panel">
      <v-data-table-server
        v-model:items-per-page="pageSize"
        v-model:page="page"
        :headers="headers"
        :items="rows"
        :items-length="total"
        :loading="loading"
        density="compact"
        :loading-text="t('data.loadingText')"
        :items-per-page-text="t('data.itemsPerPage')"
        class="page-table data-table"
        @update:options="handleOptionsChange"
      >
        <template #no-data>
          <div class="py-8 text-body-2 text-medium-emphasis text-center">
            {{ t('data.empty') }}
          </div>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            size="small"
            variant="tonal"
            color="primary"
            @click="openRecordDialog(item)"
          >
            {{ t('data.viewDetail') }}
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
                  variant="tonal"
                  color="primary"
                  @click="openRecordDialog(item)"
                >
                  {{ t('data.viewDetail') }}
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
      <v-card class="page-panel">
        <v-card-title class="d-flex align-center page-panel__title">
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
                readonly
                density="compact"
              />
              <v-text-field
                v-else-if="fieldType(field) === 'number'"
                v-model="editForm[field]"
                :label="field"
                density="compact"
                type="number"
                readonly
              />
              <v-textarea
                v-else-if="fieldType(field) === 'json'"
                v-model="editForm[field]"
                :label="field"
                density="compact"
                auto-grow
                rows="4"
                readonly
              />
              <v-text-field
                v-else
                v-model="editForm[field]"
                :label="field"
                density="compact"
                readonly
              />
            </template>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="recordDialogVisible = false">{{ t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDataRecord, getDataRecords, getDataTables } from '@/api'
import { getErrorMessage } from '@/api/client'

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
const dialogErrorMessage = ref('')
const editingRecordId = ref('')
const originalRecord = ref<Record<string, unknown>>({})
const editForm = ref<Record<string, string>>({})
const booleanEditForm = ref<Record<string, boolean>>({})
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
    errorMessage.value = getErrorMessage(error, t('data.loadFailed'))
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
    dialogErrorMessage.value = getErrorMessage(error, t('data.loadRecordFailed'))
  } finally {
    dialogLoading.value = false
  }
}

async function saveRecord() {
  return
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
  width: 180px;
  min-width: 180px;
}

:deep(.data-table .v-data-table-footer) {
  padding-top: 8px !important;
}

:deep(.data-table .v-btn) {
  min-height: 32px !important;
}

:deep(.data-table-select .v-field__input) {
  font-weight: 600;
}

@media (max-width: 960px) {
  .data-table-select {
    width: 100%;
    min-width: 0;
  }
}

.data-cell {
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
