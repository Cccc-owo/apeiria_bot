<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('permissions.title') }}</h1>
      <div class="page-actions">
        <v-btn variant="tonal" :loading="loading" @click="loadAll">{{ t('common.refresh') }}</v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <v-tabs v-model="tab" class="page-tabs">
      <v-tab value="bans">{{ t('permissions.bansTab') }}</v-tab>
      <v-tab value="users">{{ t('permissions.usersTab') }}</v-tab>
    </v-tabs>

    <v-tabs-window v-model="tab">
      <v-tabs-window-item value="bans">
        <div class="page-summary-grid mb-4">
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('permissions.totalBans') }}</div>
            <div class="summary-card__value">{{ bans.length }}</div>
          </v-sheet>
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('permissions.permanentBans') }}</div>
            <div class="summary-card__value">{{ permanentBansCount }}</div>
          </v-sheet>
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('permissions.filteredBans') }}</div>
            <div class="summary-card__value">{{ filteredBans.length }}</div>
          </v-sheet>
        </div>

        <v-card class="mb-4 page-panel permission-filter-card">
          <v-card-text class="permission-filter-bar">
            <v-text-field
              v-model="banSearch"
              :label="t('permissions.searchBans')"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              hide-details
              clearable
              class="permission-filter-bar__search"
            />
            <v-select
              v-model="banFilter"
              :items="banFilterOptions"
              :label="t('permissions.banType')"
              density="compact"
              hide-details
              class="permission-filter-bar__select"
            />
          </v-card-text>
        </v-card>

        <v-card class="mb-4 page-panel permission-create-card">
          <v-card-title class="page-panel__title permission-panel__title">
            {{ t('permissions.createBanTitle') }}
          </v-card-title>
          <v-card-text>
            <div class="compact-inline-form">
              <div class="compact-field compact-field--inline permission-field">
                <label class="compact-field__label" for="permission-user-id">{{ t('permissions.userId') }}</label>
                <v-text-field
                  id="permission-user-id"
                  v-model="banForm.user_id"
                  hide-details
                />
              </div>
              <div class="compact-field compact-field--inline permission-field">
                <label class="compact-field__label" for="permission-group-id">{{ t('permissions.groupId') }}</label>
                <v-text-field
                  id="permission-group-id"
                  v-model="banForm.group_id"
                  hide-details
                />
              </div>
              <div class="compact-field compact-field--inline permission-field">
                <label class="compact-field__label" for="permission-duration">{{ t('permissions.duration') }}</label>
                <v-text-field
                  id="permission-duration"
                  v-model.number="banForm.duration"
                  type="number"
                  hide-details
                />
              </div>
              <div class="compact-field compact-field--inline permission-field permission-field--wide">
                <label class="compact-field__label" for="permission-reason">{{ t('permissions.reason') }}</label>
                <v-text-field
                  id="permission-reason"
                  v-model="banForm.reason"
                  hide-details
                />
              </div>
              <div class="compact-inline-form__actions">
                <v-btn color="primary" :loading="creatingBan" @click="handleCreateBan">
                  {{ t('permissions.createBan') }}
                </v-btn>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <v-card class="page-panel">
          <v-data-table :headers="banHeaders" :items="filteredBans" :loading="loading" density="compact" class="page-table permission-table">
            <template #item.user_id="{ item }">
              <div class="permission-identity">
                <span class="font-weight-medium">{{ item.user_id || t('common.none') }}</span>
                <span class="text-caption text-medium-emphasis">
                  {{ t('permissions.groupLabel') }}: {{ item.group_id || t('common.none') }}
                </span>
              </div>
            </template>
            <template #item.duration="{ value }">
              {{ value === 0 ? t('permissions.permanent') : `${value}s` }}
            </template>
            <template #item.reason="{ value }">
              <span>{{ value || t('permissions.noReason') }}</span>
            </template>
            <template #item.actions="{ item }">
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                :loading="deletingBanId === item.id"
                @click="handleDeleteBan(item.id)"
              />
            </template>
            <template #no-data>
              <div class="page-table__empty">
                {{ t('permissions.noBans') }}
              </div>
            </template>
          </v-data-table>
        </v-card>
      </v-tabs-window-item>

      <v-tabs-window-item value="users">
        <div class="page-summary-grid mb-4">
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('permissions.totalUsers') }}</div>
            <div class="summary-card__value">{{ users.length }}</div>
          </v-sheet>
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('permissions.filteredUsers') }}</div>
            <div class="summary-card__value">{{ filteredUsers.length }}</div>
          </v-sheet>
          <v-sheet class="summary-card" rounded="lg">
            <div class="summary-card__label">{{ t('permissions.highLevelUsers') }}</div>
            <div class="summary-card__value">{{ highLevelUsersCount }}</div>
          </v-sheet>
        </div>

        <v-card class="mb-4 page-panel permission-filter-card">
          <v-card-text class="permission-filter-bar">
            <v-text-field
              v-model="userSearch"
              :label="t('permissions.searchUsers')"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              hide-details
              clearable
              class="permission-filter-bar__search"
            />
            <v-select
              v-model="levelFilter"
              :items="levelFilterOptions"
              :label="t('permissions.levelFilter')"
              density="compact"
              hide-details
              class="permission-filter-bar__select"
            />
          </v-card-text>
        </v-card>

        <v-card class="page-panel">
          <v-data-table :headers="userHeaders" :items="filteredUsers" :loading="loading" density="compact" class="page-table permission-table">
            <template #item.user_id="{ item }">
              <div class="permission-identity">
                <span class="font-weight-medium">{{ item.user_id }}</span>
                <span class="text-caption text-medium-emphasis">
                  {{ t('permissions.groupLabel') }}: {{ item.group_id || t('common.none') }}
                </span>
              </div>
            </template>
            <template #item.level="{ item }">
              <div class="d-flex align-center ga-2">
                <v-select
                  :model-value="item.level"
                  :items="levelOptions"
                  density="compact"
                  hide-details
                  class="level-select"
                  @update:model-value="updateLevel(item, $event)"
                />
                <v-progress-circular
                  v-if="pendingUserKey === `${item.user_id}:${item.group_id}`"
                  indeterminate
                  size="18"
                  width="2"
                />
              </div>
            </template>
            <template #no-data>
              <div class="page-table__empty">
                {{ t('permissions.noUsers') }}
              </div>
            </template>
          </v-data-table>
        </v-card>
      </v-tabs-window-item>
    </v-tabs-window>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { createBan, deleteBan, getBans, getUsers, updateUserLevel } from '@/api'
import { getErrorMessage } from '@/api/client'
import { useNoticeStore } from '@/stores/notice'

interface BanRow {
  id: number
  user_id: string | null
  group_id: string | null
  duration: number
  reason: string | null
}

interface UserLevelRow {
  user_id: string
  group_id: string
  level: number
}

const tab = ref('bans')
const bans = ref<BanRow[]>([])
const users = ref<UserLevelRow[]>([])
const loading = ref(false)
const creatingBan = ref(false)
const deletingBanId = ref<number | null>(null)
const pendingUserKey = ref('')
const errorMessage = ref('')
const banSearch = ref('')
const userSearch = ref('')
const banFilter = ref<'all' | 'permanent' | 'temporary'>('all')
const levelFilter = ref<string>('all')
const noticeStore = useNoticeStore()
const { t } = useI18n()

const levelOptions = [0, 1, 2, 3, 4, 5, 6]
const highLevelThreshold = 4

const banForm = reactive({
  user_id: '',
  group_id: '',
  duration: 0,
  reason: '',
})

const banHeaders = computed(() => [
  { title: t('permissions.user'), key: 'user_id' },
  { title: t('permissions.durationHeader'), key: 'duration' },
  { title: t('permissions.reasonHeader'), key: 'reason' },
  { title: '', key: 'actions', sortable: false },
])

const userHeaders = computed(() => [
  { title: t('permissions.user'), key: 'user_id' },
  { title: t('permissions.level'), key: 'level', sortable: false },
])

const permanentBansCount = computed(() => bans.value.filter((item) => item.duration === 0).length)
const highLevelUsersCount = computed(() => users.value.filter((item) => item.level >= highLevelThreshold).length)

const banFilterOptions = computed(() => [
  { title: t('permissions.banFilterAll'), value: 'all' },
  { title: t('permissions.banFilterPermanent'), value: 'permanent' },
  { title: t('permissions.banFilterTemporary'), value: 'temporary' },
])

const levelFilterOptions = computed(() => [
  { title: t('permissions.levelFilterAll'), value: 'all' },
  { title: t('permissions.levelFilterHigh'), value: 'high' },
  ...levelOptions.map(level => ({ title: `${t('permissions.level')} ${level}`, value: String(level) })),
])

const filteredBans = computed(() => {
  const keyword = banSearch.value.trim().toLowerCase()
  return bans.value.filter((item) => {
    const matchesKeyword = !keyword || [
      item.user_id || '',
      item.group_id || '',
      item.reason || '',
      item.duration === 0 ? t('permissions.permanent') : String(item.duration),
    ].some(value => value.toLowerCase().includes(keyword))

    const matchesFilter = banFilter.value === 'all'
      || (banFilter.value === 'permanent' && item.duration === 0)
      || (banFilter.value === 'temporary' && item.duration > 0)

    return matchesKeyword && matchesFilter
  })
})

const filteredUsers = computed(() => {
  const keyword = userSearch.value.trim().toLowerCase()
  return users.value.filter((item) => {
    const matchesKeyword = !keyword || [
      item.user_id,
      item.group_id || '',
      String(item.level),
    ].some(value => value.toLowerCase().includes(keyword))

    const matchesLevel = levelFilter.value === 'all'
      || (levelFilter.value === 'high' && item.level >= highLevelThreshold)
      || item.level === Number(levelFilter.value)

    return matchesKeyword && matchesLevel
  })
})

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [b, u] = await Promise.all([getBans(), getUsers()])
    bans.value = b.data
    users.value = u.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error, t('permissions.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function handleCreateBan() {
  if (!banForm.user_id.trim()) {
    errorMessage.value = t('permissions.userIdRequired')
    return
  }
  creatingBan.value = true
  errorMessage.value = ''
  try {
    const response = await createBan({
      user_id: banForm.user_id.trim(),
      group_id: banForm.group_id.trim() || null,
      duration: Number(banForm.duration) || 0,
      reason: banForm.reason.trim() || null,
    })
    bans.value.unshift(response.data)
    banForm.user_id = ''
    banForm.group_id = ''
    banForm.duration = 0
    banForm.reason = ''
    noticeStore.show(t('permissions.created'), 'success')
  } catch (error) {
    errorMessage.value = getErrorMessage(error, t('permissions.createFailed'))
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    creatingBan.value = false
  }
}

async function handleDeleteBan(id: number) {
  deletingBanId.value = id
  errorMessage.value = ''
  try {
    await deleteBan(id)
    bans.value = bans.value.filter((item) => item.id !== id)
    noticeStore.show(t('permissions.deleted'), 'success')
  } catch (error) {
    errorMessage.value = getErrorMessage(error, t('permissions.deleteFailed'))
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    deletingBanId.value = null
  }
}

async function updateLevel(item: UserLevelRow, nextValue: unknown) {
  const level = Number(nextValue)
  if (Number.isNaN(level) || level === item.level) {
    return
  }
  const previous = item.level
  const key = `${item.user_id}:${item.group_id}`
  item.level = level
  pendingUserKey.value = key
  errorMessage.value = ''
  try {
    await updateUserLevel(item.user_id, item.group_id, level)
    noticeStore.show(
      t('permissions.levelUpdated', { userId: item.user_id, groupId: item.group_id }),
      'success',
    )
  } catch (error) {
    item.level = previous
    errorMessage.value = getErrorMessage(error, t('permissions.levelUpdateFailed'))
    noticeStore.show(errorMessage.value, 'error')
  } finally {
    pendingUserKey.value = ''
  }
}

onMounted(() => {
  void loadAll()
})
</script>

<style scoped>
.permission-filter-card {
  background: rgb(var(--v-theme-surface-container));
}

.permission-filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.permission-filter-bar__search {
  flex: 1 1 280px;
}

.permission-filter-bar__select {
  flex: 0 0 180px;
}

.permission-identity {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}

.page-table__empty {
  padding: 20px 12px;
  color: rgba(var(--v-theme-on-surface), 0.64);
  text-align: center;
}

@media (max-width: 720px) {
  .permission-filter-bar__search,
  .permission-filter-bar__select {
    flex-basis: 100%;
  }
}
</style>

<style scoped>
.permission-panel__title {
  font-size: 0.98rem;
  font-weight: 700;
  line-height: 1.25;
}

.permission-create-card :deep(.v-card-text) {
  padding-top: 12px !important;
}

.permission-field {
  min-width: 0;
}

.permission-field--wide {
  min-width: 0;
}

.level-select {
  max-width: 110px;
}

:deep(.permission-table .v-data-table-footer) {
  padding-top: 8px !important;
}
</style>
