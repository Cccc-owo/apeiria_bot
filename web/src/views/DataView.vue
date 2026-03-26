<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('data.title') }}</h1>
      <v-spacer />
      <div class="page-toolbar-form">
        <v-text-field
          v-model.trim="search"
          class="data-search-field"
          density="compact"
          hide-details
          :label="t('data.search')"
          :placeholder="t('data.searchPlaceholder')"
          prepend-inner-icon="mdi-magnify"
          @keydown.enter.prevent="applySearch"
        />
        <v-btn :loading="loading" variant="tonal" @click="loadRecords">
          {{ t('common.refresh') }}
        </v-btn>
        <v-btn :disabled="!search" variant="text" @click="resetFilters">
          {{ t('data.resetFilters') }}
        </v-btn>
        <div class="compact-field compact-field--toolbar data-table-select">
          <label class="compact-field__label" for="data-table-select">{{ t('data.table') }}</label>
          <v-select
            id="data-table-select"
            v-model="selectedTable"
            hide-details
            item-title="label"
            item-value="name"
            :items="tableOptions"
          />
        </div>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
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
        <div class="summary-card__label">{{ t('data.primaryKey') }}</div>
        <div class="summary-card__value summary-card__value--text">{{ primaryKey }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('data.pageSize') }}</div>
        <div class="summary-card__value">{{ pageSize }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('data.searchState') }}</div>
        <div class="summary-card__value summary-card__value--text">
          {{ activeSearchText }}
        </div>
      </v-sheet>
    </div>

    <v-card class="page-panel">
      <div class="data-table-toolbar">
        <div class="data-table-toolbar__meta">
          <span>{{ t('data.currentPage', { page }) }}</span>
          <span>{{ t('data.currentRows', { count: rows.length }) }}</span>
        </div>
      </div>

      <v-data-table-server
        v-model:items-per-page="pageSize"
        v-model:page="page"
        class="page-table data-table"
        density="compact"
        :headers="headers"
        :items="rows"
        :items-length="total"
        :items-per-page-text="t('data.itemsPerPage')"
        :loading="loading"
        :loading-text="t('data.loadingText')"
        @update:options="handleOptionsChange"
      >
        <template #no-data>
          <div class="py-8 text-body-2 text-medium-emphasis text-center">
            {{ t('data.empty') }}
          </div>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            color="primary"
            size="small"
            variant="tonal"
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
              :title="String(formatCell(item[String(column.key) as keyof typeof item]))"
            >
              <template v-if="String(column.key) === 'actions'">
                <v-btn
                  color="primary"
                  size="small"
                  variant="tonal"
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
            class="mb-4"
            density="comfortable"
            type="error"
            variant="tonal"
          >
            {{ dialogErrorMessage }}
          </v-alert>

          <div v-if="dialogLoading" class="py-8 d-flex justify-center">
            <v-progress-circular color="primary" indeterminate />
          </div>

          <div v-else class="d-flex flex-column ga-4">
            <div class="data-detail-toolbar">
              <v-chip size="small" variant="tonal">
                {{ t('data.fieldCount', { count: detailFields.length }) }}
              </v-chip>
              <v-btn
                prepend-icon="mdi-content-copy"
                size="small"
                variant="tonal"
                @click="copyRecord"
              >
                {{ t('data.copyRecord') }}
              </v-btn>
            </div>
            <div v-for="field in detailFields" :key="field" class="data-detail-row">
              <div class="data-detail-row__head">
                <div class="font-weight-medium">{{ field }}</div>
                <v-btn
                  icon="mdi-content-copy"
                  size="x-small"
                  variant="text"
                  @click="copyField(field)"
                />
              </div>
              <v-chip
                v-if="fieldType(field) === 'boolean'"
                :color="originalRecord[field] ? 'success' : 'default'"
                size="small"
                variant="tonal"
              >
                {{ String(originalRecord[field]) }}
              </v-chip>
              <pre v-else-if="fieldType(field) === 'json'" class="data-detail-row__code">{{ editForm[field] }}</pre>
              <pre v-else-if="fieldType(field) === 'number'" class="data-detail-row__value data-detail-row__value--mono">{{ editForm[field] }}</pre>
              <div v-else class="data-detail-row__value">
                {{ editForm[field] }}
              </div>
            </div>
            <div>
              <div class="text-subtitle-2 mb-2">{{ t('data.rawJson') }}</div>
              <pre class="data-detail-row__code">{{ JSON.stringify(originalRecord, null, 2) }}</pre>
            </div>
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
  const search = ref('')

  const recordDialogVisible = ref(false)
  const dialogLoading = ref(false)
  const dialogErrorMessage = ref('')
  const editingRecordId = ref('')
  const originalRecord = ref<Record<string, unknown>>({})
  const editForm = ref<Record<string, string>>({})
  const { t } = useI18n()
  const noticeStore = useNoticeStore()

  const tableOptions = computed(() => tables.value)
  const selectedTableLabel = computed(
    () => tables.value.find(item => item.name === selectedTable.value)?.label || '',
  )
  const detailFields = computed(() => Object.keys(editForm.value))
  const activeSearchText = computed(() => search.value.trim() || t('data.searchIdle'))

  function formatCell (value: unknown) {
    if (value === null || value === undefined || value === '') return '-'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  function fieldType (field: string) {
    const original = originalRecord.value[field]
    if (typeof original === 'boolean') return 'boolean'
    if (typeof original === 'number') return 'number'
    if (original && typeof original === 'object') return 'json'
    return 'text'
  }

  function stringifyValue (value: unknown) {
    if (value === null || value === undefined) return ''
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  async function loadTables () {
    errorMessage.value = ''
    try {
      const response = await getDataTables()
      tables.value = response.data
      if (!selectedTable.value && tables.value.length > 0) {
        selectedTable.value = tables.value[0].name
      }
    } catch (error) {
      tables.value = []
      selectedTable.value = ''
      headers.value = []
      rows.value = []
      total.value = 0
      errorMessage.value = getErrorMessage(error, t('data.loadFailed'))
    }
  }

  async function loadRecords () {
    if (!selectedTable.value) return

    loading.value = true
    errorMessage.value = ''
    try {
      const response = await getDataRecords(selectedTable.value, page.value, pageSize.value, search.value.trim())
      primaryKey.value = response.data.primary_key
      headers.value = [
        ...response.data.columns.map(column => ({
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

  async function openRecordDialog (row: Record<string, unknown>) {
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
    } catch (error) {
      dialogErrorMessage.value = getErrorMessage(error, t('data.loadRecordFailed'))
    } finally {
      dialogLoading.value = false
    }
  }

  function applySearch () {
    page.value = 1
    void loadRecords()
  }

  function resetFilters () {
    search.value = ''
    page.value = 1
    void loadRecords()
  }

  async function copyRecord () {
    await navigator.clipboard.writeText(JSON.stringify(originalRecord.value, null, 2))
    noticeStore.show(t('data.copied'), 'success')
  }

  async function copyField (field: string) {
    await navigator.clipboard.writeText(editForm.value[field] || '')
    noticeStore.show(t('data.copied'), 'success')
  }

  function handleOptionsChange (options: { page: number; itemsPerPage: number }) {
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

  onMounted(() => {
    void loadTables()
  })
</script>

<style scoped>
.data-search-field {
  width: 240px;
  min-width: 240px;
}

.data-table-select {
  width: 180px;
  min-width: 180px;
}

.data-table-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px 0;
}

.data-table-toolbar__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 0.82rem;
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

.data-detail-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.data-detail-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.data-detail-row__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.data-detail-row__value,
.data-detail-row__code {
  margin: 0;
  padding: 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  white-space: pre-wrap;
  word-break: break-word;
}

.data-detail-row__value--mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
  font-size: 12px;
}

.data-detail-row__code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace;
  font-size: 12px;
}

@media (max-width: 960px) {
  .data-search-field,
  .data-table-select {
    width: 100%;
    min-width: 0;
  }
}
</style>
