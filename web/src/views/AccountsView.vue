<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('accounts.title') }}</h1>
      <div class="page-actions">
        <v-btn :loading="loading" variant="tonal" @click="loadData">
          {{ t('common.refresh') }}
        </v-btn>
      </div>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
      {{ errorMessage }}
    </v-alert>

    <div class="page-summary-grid mb-4">
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('accounts.totalAccounts') }}</div>
        <div class="summary-card__value">{{ accounts.length }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('accounts.totalRegistrationCodes') }}</div>
        <div class="summary-card__value">{{ registrationCodes.length }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('accounts.currentRole') }}</div>
        <div class="summary-card__value summary-card__value--text">{{ roleLabel(authStore.role) }}</div>
      </v-sheet>
      <v-sheet class="summary-card" rounded="lg">
        <div class="summary-card__label">{{ t('accounts.lastLogin') }}</div>
        <div class="summary-card__value summary-card__value--text">{{ formatTimestamp(currentAccount?.last_login_at) }}</div>
      </v-sheet>
    </div>

    <v-row>
      <v-col cols="12" lg="5">
        <v-card class="page-panel">
          <v-card-title class="page-panel__title">{{ t('accounts.passwordTitle') }}</v-card-title>
          <v-card-text class="d-flex flex-column ga-3">
            <v-text-field
              v-model="passwordForm.current_password"
              :label="t('accounts.currentPassword')"
              type="password"
            />
            <v-text-field
              v-model="passwordForm.new_password"
              :label="t('accounts.newPassword')"
              type="password"
            />
            <v-text-field
              v-model="confirmPassword"
              :error-messages="passwordError"
              :label="t('accounts.confirmPassword')"
              type="password"
            />
            <div class="d-flex justify-end">
              <v-btn color="primary" :loading="passwordSaving" @click="submitPassword">
                {{ t('accounts.changePassword') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <v-card class="page-panel mt-4">
          <v-card-title class="page-panel__title">{{ t('accounts.securityTitle') }}</v-card-title>
          <v-card-text class="d-flex flex-column ga-3">
            <div class="security-stat">
              <div class="security-stat__label">{{ t('accounts.lastLogin') }}</div>
              <div class="security-stat__value">{{ formatTimestamp(currentAccount?.last_login_at) }}</div>
            </div>
            <div class="security-stat">
              <div class="security-stat__label">{{ t('accounts.passwordChangedAt') }}</div>
              <div class="security-stat__value">{{ formatTimestamp(currentAccount?.password_changed_at) }}</div>
            </div>
            <div class="d-flex justify-end">
              <v-btn color="warning" :loading="revokingSessions" variant="tonal" @click="handleRevokeOtherSessions">
                {{ t('accounts.revokeOtherSessions') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="7">
        <v-card class="page-panel">
          <v-card-title class="page-panel__title">{{ t('accounts.registrationCodesTitle') }}</v-card-title>
          <v-card-text class="d-flex flex-column ga-4">
            <div class="account-toolbar">
              <div class="text-body-2">{{ roleLabel('owner') }}</div>
              <v-btn color="primary" :loading="registrationCodeSaving" @click="submitRegistrationCode">
                {{ t('accounts.createRegistrationCode') }}
              </v-btn>
            </div>

            <v-data-table
              class="page-table"
              density="compact"
              :headers="registrationCodeHeaders"
              :items="registrationCodes"
              :loading="loading"
            >
              <template #item.role="{ value }">
                {{ roleLabel(value) }}
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  color="error"
                  icon="mdi-delete-outline"
                  :loading="revokingCode === item.code"
                  size="small"
                  variant="text"
                  @click="handleRevokeRegistrationCode(item.code)"
                />
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="page-panel mt-4">
      <v-card-title class="page-panel__title">{{ t('accounts.accountsTitle') }}</v-card-title>
      <v-card-text>
        <v-data-table
          class="page-table"
          density="compact"
          :headers="accountHeaders"
          :items="accounts"
          :loading="loading"
        >
          <template #item.role="{ item }">
            <span>{{ roleLabel(item.role) }}</span>
          </template>
          <template #item.last_login_at="{ value }">
            <span>{{ formatTimestamp(value) }}</span>
          </template>
          <template #item.password_changed_at="{ value }">
            <span>{{ formatTimestamp(value) }}</span>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <v-card class="page-panel mt-4">
      <v-card-title class="page-panel__title">{{ t('accounts.auditTitle') }}</v-card-title>
      <v-card-text>
        <v-data-table
          class="page-table"
          density="compact"
          :headers="auditHeaders"
          :items="auditEvents"
          :loading="loading"
        >
          <template #item.event_type="{ value }">
            <span>{{ auditEventLabel(value) }}</span>
          </template>
          <template #item.occurred_at="{ value }">
            <span>{{ formatTimestamp(value) }}</span>
          </template>
          <template #item.actor_username="{ value }">
            <span>{{ value || t('common.none') }}</span>
          </template>
          <template #item.target_username="{ value }">
            <span>{{ value || t('common.none') }}</span>
          </template>
          <template #item.detail="{ value }">
            <span>{{ value || t('common.none') }}</span>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import type { RegistrationCodeItem, SecurityAuditEventItem, WebUIAccountItem } from '@/api'
  import {
    changePassword,
    createRegistrationCode,
    getAccounts,
    getRegistrationCodes,
    getSecurityAuditEvents,
    revokeOtherSessions,
    revokeRegistrationCode,
  } from '@/api'
  import { getErrorMessage } from '@/api/client'
  import { useAuthStore } from '@/stores/auth'
  import { useNoticeStore } from '@/stores/notice'

  const { t } = useI18n()
  const authStore = useAuthStore()
  const noticeStore = useNoticeStore()

  const loading = ref(false)
  const passwordSaving = ref(false)
  const registrationCodeSaving = ref(false)
  const revokingSessions = ref(false)
  const revokingCode = ref('')
  const errorMessage = ref('')
  const passwordError = ref('')
  const confirmPassword = ref('')
  const accounts = ref<WebUIAccountItem[]>([])
  const registrationCodes = ref<RegistrationCodeItem[]>([])
  const auditEvents = ref<SecurityAuditEventItem[]>([])
  const passwordForm = reactive({
    current_password: '',
    new_password: '',
  })
  const currentAccount = computed(() =>
    accounts.value.find(item => item.user_id === authStore.principal?.user_id) || null,
  )

  const accountHeaders = computed(() => [
    { title: t('accounts.username'), key: 'username' },
    { title: t('accounts.role'), key: 'role', sortable: false },
    { title: t('accounts.lastLogin'), key: 'last_login_at', sortable: false },
    { title: t('accounts.passwordChangedAt'), key: 'password_changed_at', sortable: false },
  ])
  const registrationCodeHeaders = computed(() => [
    { title: t('accounts.registrationCode'), key: 'code' },
    { title: t('accounts.role'), key: 'role', sortable: false },
    { title: t('accounts.createdBy'), key: 'created_by' },
    { title: t('accounts.createdAt'), key: 'created_at' },
    { title: t('accounts.actions'), key: 'actions', sortable: false },
  ])
  const auditHeaders = computed(() => [
    { title: t('accounts.auditTime'), key: 'occurred_at', sortable: false },
    { title: t('accounts.auditType'), key: 'event_type', sortable: false },
    { title: t('accounts.auditActor'), key: 'actor_username', sortable: false },
    { title: t('accounts.auditTarget'), key: 'target_username', sortable: false },
    { title: t('accounts.auditDetail'), key: 'detail', sortable: false },
  ])
  function roleLabel (role: string) {
    if (role === 'owner') {
      return t('accounts.roles.owner')
    }
    return role || t('common.none')
  }

  function formatTimestamp (value: string | null | undefined) {
    if (!value) {
      return t('common.none')
    }
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return value
    }
    return date.toLocaleString()
  }

  function auditEventLabel (eventType: string) {
    return t(`accounts.auditEvents.${eventType}`)
  }

  async function loadData () {
    loading.value = true
    errorMessage.value = ''
    try {
      const [accountsResponse, registrationCodesResponse, auditEventsResponse] = await Promise.all([
        getAccounts(),
        getRegistrationCodes(),
        getSecurityAuditEvents(),
      ])
      accounts.value = accountsResponse.data
      registrationCodes.value = registrationCodesResponse.data
      auditEvents.value = auditEventsResponse.data
    } catch (err) {
      errorMessage.value = getErrorMessage(err, t('accounts.loadFailed'))
    } finally {
      loading.value = false
    }
  }

  async function submitPassword () {
    if (!passwordForm.current_password || !passwordForm.new_password || !confirmPassword.value) {
      passwordError.value = t('accounts.passwordIncomplete')
      return
    }
    if (passwordForm.new_password !== confirmPassword.value) {
      passwordError.value = t('register.passwordMismatch')
      return
    }
    passwordSaving.value = true
    passwordError.value = ''
    try {
      const response = await changePassword(passwordForm)
      authStore.acceptSession(response.data.token, response.data.principal)
      noticeStore.show(response.data.detail || t('accounts.passwordChanged'), 'success')
      passwordForm.current_password = ''
      passwordForm.new_password = ''
      confirmPassword.value = ''
      await loadData()
    } catch (err) {
      passwordError.value = getErrorMessage(err, t('accounts.passwordChangeFailed'))
    } finally {
      passwordSaving.value = false
    }
  }

  async function submitRegistrationCode () {
    registrationCodeSaving.value = true
    try {
      const response = await createRegistrationCode({ role: 'owner' })
      registrationCodes.value = [response.data, ...registrationCodes.value]
      noticeStore.show(t('accounts.registrationCodeCreated'), 'success')
    } catch (err) {
      errorMessage.value = getErrorMessage(err, t('accounts.registrationCodeCreateFailed'))
    } finally {
      registrationCodeSaving.value = false
    }
  }

  async function handleRevokeRegistrationCode (code: string) {
    revokingCode.value = code
    try {
      await revokeRegistrationCode(code)
      registrationCodes.value = registrationCodes.value.filter(item => item.code !== code)
      noticeStore.show(t('accounts.registrationCodeRevoked'), 'success')
    } catch (err) {
      errorMessage.value = getErrorMessage(err, t('accounts.registrationCodeRevokeFailed'))
    } finally {
      revokingCode.value = ''
    }
  }

  async function handleRevokeOtherSessions () {
    revokingSessions.value = true
    try {
      const response = await revokeOtherSessions()
      authStore.acceptSession(response.data.token, response.data.principal)
      noticeStore.show(response.data.detail || t('accounts.otherSessionsRevoked'), 'success')
      await loadData()
    } catch (err) {
      errorMessage.value = getErrorMessage(err, t('accounts.revokeOtherSessionsFailed'))
    } finally {
      revokingSessions.value = false
    }
  }

  onMounted(loadData)
</script>

<style scoped>
.account-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.security-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.security-stat__label {
  color: rgba(var(--v-theme-on-surface), 0.64);
  font-size: 0.82rem;
}

.security-stat__value {
  font-weight: 600;
}
</style>
