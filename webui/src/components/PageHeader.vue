<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>();
</script>

<template>
  <!-- Option 2 (MUI-style): the page title lives in the top app bar, so the
       content header only carries the subtitle + primary actions. -->
  <div
    v-if="subtitle || $slots.actions"
    class="mb-5 flex min-h-9 flex-wrap items-center justify-between gap-x-4 gap-y-2"
  >
    <p v-if="subtitle" class="min-w-0 text-sm text-muted-foreground">
      {{ subtitle }}
    </p>
    <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
