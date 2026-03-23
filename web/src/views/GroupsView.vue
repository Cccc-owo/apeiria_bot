<template>
  <div class="d-flex flex-column ga-6">
    <div class="d-flex align-center justify-space-between flex-wrap ga-3">
      <h1 class="text-h4">{{ t('groups.title') }}</h1>
      <v-btn variant="tonal" :loading="loading" @click="loadGroups">{{ t('common.refresh') }}</v-btn>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <div class="d-flex flex-wrap ga-3">
      <v-sheet class="summary-card" rounded="lg" border>
        <div class="text-caption text-medium-emphasis">{{ t('groups.totalCount') }}</div>
        <div class="text-h5 font-weight-bold">{{ groups.length }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg" border>
        <div class="text-caption text-medium-emphasis">{{ t('groups.enabledCount') }}</div>
        <div class="text-h5 font-weight-bold">{{ enabledGroupsCount }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg" border>
        <div class="text-caption text-medium-emphasis">{{ t('groups.customizedCount') }}</div>
        <div class="text-h5 font-weight-bold">{{ customizedGroupsCount }}</div>
      </v-sheet>
    </div>

    <v-card>
      <v-data-table :headers="headers" :items="groups" :loading="loading" density="comfortable">
        <template #item.group_name="{ item }">
          <div class="d-flex flex-column py-2">
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
      <v-card>
        <v-card-title>{{ t('groups.dialogTitle') }}</v-card-title>
        <v-card-text class="d-flex flex-column ga-4">
          <div class="text-body-2 text-medium-emphasis">
            {{ t('groups.currentGroup', { groupId: editingGroup?.group_id ?? '' }) }}
          </div>
          <v-alert type="info" variant="tonal" density="comfortable">
            {{ t('groups.protectedInfo') }}
          </v-alert>
          <v-autocomplete
            v-model="selectedDisabledPlugins"
            :items="pluginOptions"
            item-title="title"
            item-value="value"
            :label="t('groups.disabledPlugins')"
            chips
            closable-chips
            multiple
            variant="outlined"
            density="comfortable"
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
      .filter((item: { is_protected?: boolean }) => !item.is_protected)
      .map((item: { module_name: string; name: string | null }) => ({
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
.summary-card {
  min-width: 168px;
  padding: 16px 18px;
}
</style>
