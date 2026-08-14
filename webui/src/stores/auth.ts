import { defineStore } from "pinia";
import { ref } from "vue";

export const useAuthStore = defineStore(
  "auth",
  () => {
    const token = ref<string | null>(null);
    const username = ref<string | null>(null);
    const mustChangePassword = ref(false);

    function setSession(t: string, u: string, mustChange = false) {
      token.value = t;
      username.value = u;
      mustChangePassword.value = mustChange;
    }

    function clearMustChangePassword() {
      mustChangePassword.value = false;
    }

    function clearSession() {
      token.value = null;
      username.value = null;
      mustChangePassword.value = false;
    }

    return {
      token,
      username,
      mustChangePassword,
      setSession,
      clearMustChangePassword,
      clearSession,
    };
  },
  {
    // Token persisted in localStorage for session survival across page refreshes.
    // Acceptable for intranet admin dashboards protected by host-level auth.
    // For public deployments, migrate to HttpOnly cookie + CSRF token flow.
    persist: true,
  },
);
