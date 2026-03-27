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
        </v-data-table>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import type { RegistrationCodeItem, WebUIAccountItem } from '@/api'
  import {
    changePassword,
    createRegistrationCode,
    getAccounts,
    getRegistrationCodes,
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
  const revokingCode = ref('')
  const errorMessage = ref('')
  const passwordError = ref('')
  const confirmPassword = ref('')
  const accounts = ref<WebUIAccountItem[]>([])
  const registrationCodes = ref<RegistrationCodeItem[]>([])
  const passwordForm = reactive({
    current_password: '',
    new_password: '',
  })

  const accountHeaders = computed(() => [
    { title: t('accounts.username'), key: 'username' },
    { title: t('accounts.role'), key: 'role', sortable: false },
  ])
  const registrationCodeHeaders = computed(() => [
    { title: t('accounts.registrationCode'), key: 'code' },
    { title: t('accounts.role'), key: 'role', sortable: false },
    { title: t('accounts.createdBy'), key: 'created_by' },
    { title: t('accounts.createdAt'), key: 'created_at' },
    { title: t('accounts.actions'), key: 'actions', sortable: false },
  ])
  function roleLabel (role: string) {
    if (role === 'owner') {
      return t('accounts.roles.owner')
    }
    return role || t('common.none')
  }

  async function loadData () {
    loading.value = true
    errorMessage.value = ''
    try {
      const [accountsResponse, invitesResponse] = await Promise.all([
        getAccounts(),
        getRegistrationCodes(),
      ])
      accounts.value = accountsResponse.data
      registrationCodes.value = invitesResponse.data
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
      noticeStore.show(response.data.detail || t('accounts.passwordChanged'), 'success')
      passwordForm.current_password = ''
      passwordForm.new_password = ''
      confirmPassword.value = ''
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

  onMounted(loadData)
</script>

<style scoped>
.account-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>
