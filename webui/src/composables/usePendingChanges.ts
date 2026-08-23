import { ref } from "vue";

/**
 * Per-view "pending changes" flag. Each caller gets its own ref so that
 * changes made on one page (e.g. enabling a plugin) do not show a stale
 * "pending changes" banner on other pages. It is a soft, dismissible
 * reminder scoped to the current view.
 */
export function usePendingChanges() {
  const pendingChanges = ref(false);

  return {
    pendingChanges,
    markChanged: () => {
      pendingChanges.value = true;
    },
    clearChanges: () => {
      pendingChanges.value = false;
    },
  };
}
