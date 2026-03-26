<template>
  <v-container class="fill-height auth-view" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card class="auth-card">
          <v-card-title class="auth-card__title">
            <v-icon size="40" color="primary">mdi-account-plus</v-icon>
            <div class="auth-card__brand">
              <div class="auth-card__name">{{ t('layout.brand') }}</div>
              <div class="auth-card__subtitle">{{ t('register.description') }}</div>
            </div>
          </v-card-title>

          <v-card-text>
            <v-form @submit.prevent="handleRegister">
              <v-text-field
                v-model.trim="inviteCode"
                :label="t('register.inviteCode')"
                prepend-inner-icon="mdi-ticket-confirmation-outline"
                autocomplete="one-time-code"
                autofocus
              />
              <v-text-field
                v-model.trim="username"
                :label="t('register.username')"
                prepend-inner-icon="mdi-account"
                autocomplete="username"
              />
              <v-text-field
                v-model="password"
                :label="t('register.password')"
                prepend-inner-icon="mdi-lock"
                type="password"
                autocomplete="new-password"
              />
              <v-text-field
                v-model="confirmPassword"
                :label="t('register.confirmPassword')"
                prepend-inner-icon="mdi-lock-check"
                type="password"
                :error-messages="error"
                autocomplete="new-password"
              />
              <v-btn
                type="submit"
                color="primary"
                block
                size="large"
                :loading="loading"
                class="mt-4"
              >
                {{ t('register.submit') }}
              </v-btn>
              <v-btn
                block
                variant="text"
                class="mt-2"
                @click="router.push('/login')"
              >
                {{ t('register.toLogin') }}
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { register } from '@/api'
import { getErrorMessage } from '@/api/client'
import { useNoticeStore } from '@/stores/notice'

const inviteCode = ref('')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)
const { t } = useI18n()
const router = useRouter()
const noticeStore = useNoticeStore()

async function handleRegister() {
  if (!inviteCode.value.trim() || !username.value.trim() || !password.value || !confirmPassword.value) {
    error.value = t('register.missingFields')
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = t('register.passwordMismatch')
    return
  }

  loading.value = true
  error.value = ''
  try {
    const response = await register({
      invite_code: inviteCode.value.trim(),
      username: username.value.trim(),
      password: password.value,
    })
    noticeStore.show(response.data.detail || t('register.success'), 'success')
    router.push('/login')
  } catch (err) {
    error.value = getErrorMessage(err, t('register.failed'))
  } finally {
    loading.value = false
  }
}
</script>
