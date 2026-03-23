<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('groups.title') }}</h1>
      <div class="page-actions">
        <v-btn variant="tonal" :loading="loading" @click="loadGroups">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <div class="page-summary-grid">
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('groups.totalCount') }}</div>
        <div class="summary-card__value">{{ groups.length }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('groups.enabledCount') }}</div>
        <div class="summary-card__value">{{ enabledGroupsCount }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('groups.customizedCount') }}</div>
        <div class="summary-card__value">{{ customizedGroupsCount }}</div>
      </v-sheet>
    </div>

    <v-card class="page-panel">
      <v-data-table :headers="headers" :items="groups" :loading="loading" density="compact" class="page-table groups-table">
        <template #item.group_name="{ item }">
          <div class="groups-table__name">
            <span class="font-weight-medium">{{ item.group_name || t('groups.unnamed') }}</span>
            <span class="text-caption text-medium-emphasis">{{ item.group_id }}</span>
          </div>
        </template>
        <template #item.bot_status="{ item }">
          <v-switch
            :model-value="item.bot_status"
            color="success"
            hide-details
            inset
            :loading="pendingGroupId === item.group_id"
            @update:model-value="toggleGroupStatus(item, $event)"
          />
        </template>
        <template #item.disabled_plugins="{ value }">
          <span v-if="value.length === 0" class="text-medium-emphasis">{{ t('common.none') }}</span>
          <v-chip v-for="plugin in value" :key="plugin" size="x-small" class="mr-1 mb-1" color="warning" variant="tonal">
            {{ plugin }}
          </v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn size="small" variant="tonal" color="primary" @click="openPluginDialog(item)">
            {{ t('groups.settings') }}
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="pluginDialogVisible" max-width="640">
      <v-card class="page-panel">
        <v-card-title class="page-panel__title">{{ t('groups.dialogTitle') }}</v-card-title>
        <v-card-text class="group-dialog">
          <div class="group-dialog__meta">
            {{ t('groups.currentGroup', { groupId: editingGroup?.group_id ?? '' }) }}
          </div>
          <v-autocomplete
            v-model="selectedDisabledPlugins"
            :items="pluginOptions"
            item-title="title"
            item-value="value"
            :label="t('groups.disabledPlugins')"
            chips
            closable-chips
            multiple
            density="compact"
            class="group-dialog__field"
          />
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="pluginDialogVisible = false">{{ t('common.cancel') }}</v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="savingPlugins" @click="saveGroupPlugins">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getGroups, getPlugins, updateGroup, updateGroupPlugins } from '@/api'
import { useNoticeStore } from '@/stores/notice'

interface GroupRow {
  group_id: string
  group_name: string | null
  bot_status: boolean
  disabled_plugins: string[]
}

interface PluginOption {
  title: string
  value: string
  disabled?: boolean
}

interface PluginListItem {
  module_name: string
  name: string | null
  source?: string
}

const groups = ref<GroupRow[]>([])
const pluginOptions = ref<PluginOption[]>([])
const loading = ref(false)
const pendingGroupId = ref('')
const errorMessage = ref('')
const pluginDialogVisible = ref(false)
const savingPlugins = ref(false)
const editingGroup = ref<GroupRow | null>(null)
const selectedDisabledPlugins = ref<string[]>([])
const noticeStore = useNoticeStore()
const { t } = useI18n()

const headers = computed(() => [
  { title: t('groups.name'), key: 'group_name' },
  { title: t('groups.botStatus'), key: 'bot_status', sortable: false },
  { title: t('groups.disabledPluginsHeader'), key: 'disabled_plugins', sortable: false },
  { title: t('groups.actions'), key: 'actions', sortable: false },
])

const enabledGroupsCount = computed(() => groups.value.filter((item) => item.bot_status).length)
const customizedGroupsCount = computed(() => groups.value.filter((item) => item.disabled_plugins.length > 0).length)

async function loadGroups() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [groupsResponse, pluginsResponse] = await Promise.all([getGroups(), getPlugins()])
    groups.value = groupsResponse.data
    pluginOptions.value = pluginsResponse.data
      .filter((item: PluginListItem) => item.source !== 'framework')
      .map((item: PluginListItem) => ({
        title: item.name || item.module_name,
        value: item.module_name,
      }))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('groups.loadFailed')
  } finally {
    loading.value = false
  }
}

async function toggleGroupStatus(item: GroupRow, nextValue: boolean | null) {
  const botStatus = Boolean(nextValue)
  const previous = item.bot_status
  item.bot_status = botStatus
  pendingGroupId.value = item.group_id
  errorMessage.value = ''
  try {
    await updateGroup(item.group_id, botStatus)
    noticeStore.show(
      t('groups.botUpdated', {
        groupId: item.group_id,
        action: botStatus ? t('groups.enabled') : t('groups.disabled'),
      }),
      'success',
    )
  } catch (error) {
    item.bot_status = previous
    errorMessage.value = error instanceof Error ? error.message : t('groups.updateFailed')
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    pendingGroupId.value = ''
  }
}

function openPluginDialog(item: GroupRow) {
  editingGroup.value = item
  selectedDisabledPlugins.value = [...item.disabled_plugins]
  pluginDialogVisible.value = true
}

async function saveGroupPlugins() {
  if (!editingGroup.value) return
  savingPlugins.value = true
  errorMessage.value = ''
  try {
    await updateGroupPlugins(editingGroup.value.group_id, selectedDisabledPlugins.value)
    editingGroup.value.disabled_plugins = [...selectedDisabledPlugins.value]
    pluginDialogVisible.value = false
    noticeStore.show(
      t('groups.settingsSaved', { groupId: editingGroup.value.group_id }),
      'success',
    )
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('groups.settingsSaveFailed')
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    savingPlugins.value = false
  }
}

onMounted(() => {
  void loadGroups()
})
</script>

<style scoped>
.group-dialog {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-dialog__meta {
  color: rgba(var(--v-theme-on-surface), 0.64);
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.2;
}

.groups-table__name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}
</style>
