import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WebUIPrincipal } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const isLoggedIn = ref(!!token.value)
  const principal = ref<WebUIPrincipal | null>(readPrincipal())

  function setSession(nextToken: string, nextPrincipal: WebUIPrincipal) {
    token.value = nextToken
    isLoggedIn.value = true
    principal.value = nextPrincipal
    localStorage.setItem('token', nextToken)
    localStorage.setItem('apeiria-principal', JSON.stringify(nextPrincipal))
  }

  function setPrincipal(nextPrincipal: WebUIPrincipal | null) {
    principal.value = nextPrincipal
    if (!nextPrincipal) {
      localStorage.removeItem('apeiria-principal')
      return
    }
    localStorage.setItem('apeiria-principal', JSON.stringify(nextPrincipal))
  }

  function setToken(t: string) {
    token.value = t
    isLoggedIn.value = true
    localStorage.setItem('token', t)
  }

  function logout() {
    token.value = ''
    isLoggedIn.value = false
    principal.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('apeiria-principal')
  }

  return { token, isLoggedIn, principal, setSession, setPrincipal, setToken, logout }
})

function readPrincipal(): WebUIPrincipal | null {
  const raw = localStorage.getItem('apeiria-principal')
  if (!raw) return null
  try {
    return JSON.parse(raw) as WebUIPrincipal
  } catch {
    localStorage.removeItem('apeiria-principal')
    return null
  }
}
