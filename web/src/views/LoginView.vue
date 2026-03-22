<template>
  <v-container class="fill-height login-view" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4">
        <v-card class="pa-6 login-card" elevation="10">
          <v-card-title class="text-center text-h5 mb-4">
            <v-icon size="48" color="primary" class="mr-2">mdi-robot-happy</v-icon>
            <div>Apeiria Bot</div>
          </v-card-title>

          <v-card-text>
            <div class="text-medium-emphasis text-center mb-5">
              {{ t('login.description') }}
            </div>
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
.login-view {
  background:
    radial-gradient(circle at top center, rgba(var(--v-theme-primary), 0.14), transparent 32%),
    linear-gradient(180deg, rgba(var(--v-theme-surface), 0.42), rgba(var(--v-theme-background), 0.92));
}

.login-card {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  background: rgba(var(--v-theme-surface), 0.92);
  backdrop-filter: blur(18px);
}
</style>
