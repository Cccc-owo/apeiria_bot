<template>
  <v-container class="fill-height auth-view" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4" lg="3">
        <v-card class="auth-card">
          <v-card-title class="auth-card__title">
            <v-icon size="40" color="primary">mdi-robot-happy</v-icon>
            <div class="auth-card__brand">
              <div class="auth-card__name">Apeiria Console</div>
              <div class="auth-card__subtitle">{{ t('login.description') }}</div>
            </div>
          </v-card-title>

          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="password"
                :label="t('login.password')"
                type="password"
                prepend-inner-icon="mdi-lock"
                :error-messages="error"
                autofocus
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
import { useAuthStore } from '@/stores/auth'

const password = ref('')
const error = ref('')
const loading = ref(false)
const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const res = await login(password.value)
    authStore.setToken(res.data.token)
    router.push('/dashboard')
  } catch {
    error.value = t('login.wrongPassword')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
</style>
