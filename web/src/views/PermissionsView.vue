<template>
  <div class="d-flex flex-column ga-6">
    <div class="d-flex align-center justify-space-between flex-wrap ga-3">
      <h1 class="text-h4">{{ t('permissions.title') }}</h1>
      <v-btn variant="tonal" :loading="loading" @click="loadAll">{{ t('common.refresh') }}</v-btn>
    </div>

    <v-alert v-if="errorMessage" type="error" variant="tonal" density="comfortable">
      {{ errorMessage }}
    </v-alert>

    <v-tabs v-model="tab">
      <v-tab value="bans">{{ t('permissions.bansTab') }}</v-tab>
      <v-tab value="users">{{ t('permissions.usersTab') }}</v-tab>
    </v-tabs>

    <v-tabs-window v-model="tab">
      <v-tabs-window-item value="bans">
        <v-card class="mb-4">
          <v-card-title>{{ t('permissions.createBanTitle') }}</v-card-title>
          <v-card-text class="d-flex flex-wrap ga-3">
            <v-text-field
              v-model="banForm.user_id"
              :label="t('permissions.userId')"
              variant="outlined"
              density="comfortable"
              hide-details
              class="permission-field"
            />
            <v-text-field
              v-model="banForm.group_id"
              :label="t('permissions.groupId')"
              variant="outlined"
              density="comfortable"
              hide-details
              class="permission-field"
            />
            <v-text-field
              v-model.number="banForm.duration"
              :label="t('permissions.duration')"
              variant="outlined"
              density="comfortable"
              hide-details
              type="number"
              class="permission-field"
            />
            <v-text-field
              v-model="banForm.reason"
              :label="t('permissions.reason')"
              variant="outlined"
              density="comfortable"
              hide-details
              class="permission-field permission-field--wide"
            />
            <v-btn color="primary" :loading="creatingBan" @click="handleCreateBan">
              {{ t('permissions.createBan') }}
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card>
          <v-data-table :headers="banHeaders" :items="bans" :loading="loading" density="comfortable">
            <template #item.duration="{ value }">
              {{ value === 0 ? t('permissions.permanent') : `${value}s` }}
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
          </v-data-table>
        </v-card>
      </v-tabs-window-item>

      <v-tabs-window-item value="users">
        <v-card>
          <v-data-table :headers="userHeaders" :items="users" :loading="loading" density="comfortable">
            <template #item.level="{ item }">
              <div class="d-flex align-center ga-2">
                <v-select
                  :model-value="item.level"
                  :items="levelOptions"
                  density="compact"
                  variant="outlined"
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
const noticeStore = useNoticeStore()
const { t } = useI18n()

const levelOptions = [0, 1, 2, 3, 4, 5, 6]

const banForm = reactive({
  user_id: '',
  group_id: '',
  duration: 0,
  reason: '',
})

const banHeaders = computed(() => [
  { title: t('permissions.user'), key: 'user_id' },
  { title: t('permissions.group'), key: 'group_id' },
  { title: t('permissions.durationHeader'), key: 'duration' },
  { title: t('permissions.reasonHeader'), key: 'reason' },
  { title: '', key: 'actions', sortable: false },
])

const userHeaders = computed(() => [
  { title: t('permissions.user'), key: 'user_id' },
  { title: t('permissions.group'), key: 'group_id' },
  { title: t('permissions.level'), key: 'level', sortable: false },
])

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [b, u] = await Promise.all([getBans(), getUsers()])
    bans.value = b.data
    users.value = u.data
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('permissions.loadFailed')
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
    errorMessage.value = error instanceof Error ? error.message : t('permissions.createFailed')
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
    errorMessage.value = error instanceof Error ? error.message : t('permissions.deleteFailed')
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
    errorMessage.value = error instanceof Error ? error.message : t('permissions.levelUpdateFailed')
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
.permission-field {
  min-width: 180px;
  max-width: 240px;
}

.permission-field--wide {
  min-width: 240px;
  max-width: 320px;
}

.level-select {
  max-width: 110px;
}
</style>
