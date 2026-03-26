<template>
  <v-container class="fill-height auth-view" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4" lg="3">
        <v-card class="auth-card">
          <v-card-title class="auth-card__title">
            <v-icon size="40" color="primary">mdi-robot-happy</v-icon>
            <div class="auth-card__brand">
              <div class="auth-card__name">{{ t('layout.brand') }}</div>
              <div class="auth-card__subtitle">{{ t('login.description') }}</div>
            </div>
          </v-card-title>

          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model.trim="username"
                :label="t('login.username')"
                prepend-inner-icon="mdi-account"
                autocomplete="username"
                autofocus
              />
              <v-text-field
                v-model="password"
                :label="t('login.password')"
                type="password"
                prepend-inner-icon="mdi-lock"
                :error-messages="error"
                autocomplete="current-password"
              />
              <v-btn
                type="submit"
                color="primary"
                block
                size="large"
                :loading="loading"
                class="mt-4"
              >
                {{ t('login.submit') }}
              </v-btn>
              <v-btn
                block
                variant="text"
                class="mt-2"
                @click="router.push('/register')"
              >
                {{ t('login.toRegister') }}
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
import { login } from '@/api'
import { getErrorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    error.value = t('login.missingFields')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await login({
      username: username.value.trim(),
      password: password.value,
    })
    authStore.setSession(res.data.token, res.data.principal)
    router.push('/dashboard')
  } catch (err) {
    error.value = getErrorMessage(err, t('login.wrongPassword'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
</style>
