<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('groups.title') }}</h1>
      <div class="page-actions">
        <v-btn :loading="loading" variant="tonal" @click="loadGroups">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
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
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('groups.filteredCount') }}</div>
        <div class="summary-card__value">{{ filteredGroups.length }}</div>
      </v-sheet>
    </div>

    <v-card class="page-panel groups-filter-card">
      <v-card-text class="groups-filter-bar">
        <v-text-field
          v-model="search"
          class="groups-filter-bar__search"
          clearable
          density="compact"
          hide-details
          :label="t('groups.search')"
          prepend-inner-icon="mdi-magnify"
        />
        <v-select
          v-model="statusFilter"
          class="groups-filter-bar__select"
          density="compact"
          hide-details
          :items="statusFilterOptions"
          :label="t('groups.statusFilter')"
        />
        <v-select
          v-model="pluginFilter"
          class="groups-filter-bar__select"
          density="compact"
          hide-details
          :items="pluginFilterOptions"
          :label="t('groups.pluginFilter')"
        />
      </v-card-text>
    </v-card>

    <v-card class="page-panel">
      <v-data-table
        class="page-table groups-table"
        density="compact"
        :headers="headers"
        :items="filteredGroups"
        :loading="loading"
      >
        <template #item.group_name="{ item }">
          <div class="groups-table__name">
            <span class="font-weight-medium">{{ item.group_name || t('groups.unnamed') }}</span>
            <span class="text-caption text-medium-emphasis">{{ item.group_id }}</span>
          </div>
        </template>
        <template #item.bot_status="{ item }">
          <v-switch
            color="success"
            hide-details
            inset
            :loading="pendingGroupId === item.group_id"
            :model-value="item.bot_status"
            @update:model-value="toggleGroupStatus(item, $event)"
          />
        </template>
        <template #item.disabled_plugins="{ value }">
          <div class="groups-table__plugins">
            <span v-if="value.length === 0" class="text-medium-emphasis">{{ t('common.none') }}</span>
            <template v-else>
              <v-chip
                v-for="plugin in value.slice(0, 3)"
                :key="plugin"
                color="warning"
                size="x-small"
                variant="tonal"
              >
                {{ plugin }}
              </v-chip>
              <span v-if="value.length > 3" class="text-caption text-medium-emphasis">
                {{ t('groups.morePlugins', { count: value.length - 3 }) }}
              </span>
            </template>
          </div>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="primary" size="small" variant="tonal" @click="openPluginDialog(item)">
            {{ t('groups.settings') }}
          </v-btn>
        </template>
        <template #no-data>
          <div class="page-table__empty">
            {{ t('groups.noGroups') }}
          </div>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="pluginDialogVisible" max-width="640">
      <v-card class="page-panel">
        <v-card-title class="page-panel__title">{{ t('groups.dialogTitle') }}</v-card-title>
        <v-card-text class="group-dialog">
          <div class="group-dialog__summary">
            <div class="group-dialog__name">
              {{ editingGroup?.group_name || t('groups.unnamed') }}
            </div>
            <div class="group-dialog__meta">
              {{ t('groups.currentGroup', { groupId: editingGroup?.group_id ?? '' }) }}
            </div>
          </div>
          <v-alert
            v-if="protectedPluginCount > 0"
            density="comfortable"
            type="info"
            variant="tonal"
          >
            {{ t('groups.protectedInfo') }}
          </v-alert>
          <v-autocomplete
            v-model="selectedDisabledPlugins"
            chips
            class="group-dialog__field"
            closable-chips
            density="compact"
            item-title="title"
            item-value="value"
            :items="pluginOptions"
            :label="t('groups.disabledPlugins')"
            multiple
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
  import { computed, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
  import { getGroups, getPlugins, updateGroup, updateGroupPlugins } from '@/api'
  import type { PluginItem } from '@/api'
  import { getErrorMessage } from '@/api/client'
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
  const protectedPluginCount = ref(0)
  const loading = ref(false)
  const pendingGroupId = ref('')
  const errorMessage = ref('')
  const pluginDialogVisible = ref(false)
  const savingPlugins = ref(false)
  const editingGroup = ref<GroupRow | null>(null)
  const selectedDisabledPlugins = ref<string[]>([])
  const search = ref('')
  const statusFilter = ref<'all' | 'enabled' | 'disabled'>('all')
  const pluginFilter = ref<'all' | 'customized' | 'clean'>('all')
  const noticeStore = useNoticeStore()
  const { t } = useI18n()
  const route = useRoute()

  const headers = computed(() => [
    { title: t('groups.name'), key: 'group_name' },
    { title: t('groups.botStatus'), key: 'bot_status', sortable: false },
    { title: t('groups.disabledPluginsHeader'), key: 'disabled_plugins', sortable: false },
    { title: t('groups.actions'), key: 'actions', sortable: false },
  ])

  const enabledGroupsCount = computed(() => groups.value.filter(item => item.bot_status).length)
  const customizedGroupsCount = computed(() => groups.value.filter(item => item.disabled_plugins.length > 0).length)

  const statusFilterOptions = computed(() => [
    { title: t('groups.statusAll'), value: 'all' },
    { title: t('groups.statusEnabled'), value: 'enabled' },
    { title: t('groups.statusDisabled'), value: 'disabled' },
  ])

  const pluginFilterOptions = computed(() => [
    { title: t('groups.pluginFilterAll'), value: 'all' },
    { title: t('groups.pluginFilterCustomized'), value: 'customized' },
    { title: t('groups.pluginFilterClean'), value: 'clean' },
  ])

  const filteredGroups = computed(() => {
    const keyword = search.value.trim().toLowerCase()
    return groups.value.filter(item => {
      const matchesKeyword = !keyword || [
        item.group_id,
        item.group_name || '',
        ...item.disabled_plugins,
      ].some(value => value.toLowerCase().includes(keyword))

      const matchesStatus = statusFilter.value === 'all'
        || (statusFilter.value === 'enabled' && item.bot_status)
        || (statusFilter.value === 'disabled' && !item.bot_status)

      const matchesPluginState = pluginFilter.value === 'all'
        || (pluginFilter.value === 'customized' && item.disabled_plugins.length > 0)
        || (pluginFilter.value === 'clean' && item.disabled_plugins.length === 0)

      return matchesKeyword && matchesStatus && matchesPluginState
    })
  })

  function applyRouteFilters () {
    const statusQuery = route.query.status
    if (
      statusQuery === 'all'
      || statusQuery === 'enabled'
      || statusQuery === 'disabled'
    ) {
      statusFilter.value = statusQuery
    }
  }

  async function loadGroups () {
    loading.value = true
    errorMessage.value = ''
    try {
      const [groupsResponse, pluginsResponse] = await Promise.all([getGroups(), getPlugins()])
      groups.value = groupsResponse.data
      protectedPluginCount.value = pluginsResponse.data.filter(
        (item: PluginItem) => item.source !== 'framework' && item.is_protected,
      ).length
      pluginOptions.value = pluginsResponse.data
        .filter((item: PluginItem) => item.source !== 'framework' && !item.is_protected)
        .map((item: PluginItem) => ({
          title: item.name || item.module_name,
          value: item.module_name,
        }))
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('groups.loadFailed'))
    } finally {
      loading.value = false
    }
  }

  async function toggleGroupStatus (item: GroupRow, nextValue: boolean | null) {
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
      errorMessage.value = getErrorMessage(error, t('groups.updateFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      pendingGroupId.value = ''
    }
  }

  function openPluginDialog (item: GroupRow) {
    editingGroup.value = item
    selectedDisabledPlugins.value = [...item.disabled_plugins]
    pluginDialogVisible.value = true
  }

  async function saveGroupPlugins () {
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
      errorMessage.value = getErrorMessage(error, t('groups.settingsSaveFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      savingPlugins.value = false
    }
  }

  onMounted(() => {
    applyRouteFilters()
    void loadGroups()
  })
  watch(() => route.query, () => {
    applyRouteFilters()
  })
</script>

<style scoped>
.groups-filter-card {
  margin-top: 16px;
  margin-bottom: 16px;
  background: rgb(var(--v-theme-surface-container));
}

.groups-filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.groups-filter-bar__search {
  flex: 1 1 280px;
}

.groups-filter-bar__select {
  flex: 0 0 180px;
}

.group-dialog {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-dialog__summary {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.group-dialog__name {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.3;
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

.groups-table__plugins {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.page-table__empty {
  padding: 20px 12px;
  color: rgba(var(--v-theme-on-surface), 0.64);
  text-align: center;
}

@media (max-width: 720px) {
  .groups-filter-bar__search,
  .groups-filter-bar__select {
    flex-basis: 100%;
  }
}
</style>
