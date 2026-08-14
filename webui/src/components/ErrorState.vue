<script setup lang="ts">
import { AlertCircle } from "@lucide/vue";
import { Button } from "@/components/ui/button";

defineProps<{ message?: string }>();
defineEmits<{ retry: [] }>();
</script>

<template>
  <div class="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
    <div class="flex items-start gap-3">
      <div
        class="flex size-8 shrink-0 items-center justify-center rounded-full bg-destructive/10"
      >
        <AlertCircle class="size-4 text-destructive" aria-hidden="true" />
      </div>
      <div class="min-w-0 flex-1">
        <p class="text-sm font-medium">{{ $t("error.loadFailed") }}</p>
        <p v-if="message" class="mt-0.5 break-words text-sm text-muted-foreground">
          {{ message }}
        </p>
        <Button variant="outline" size="sm" class="mt-3" @click="$emit('retry')">
          {{ $t("error.retry") }}
        </Button>
      </div>
    </div>
  </div>
</template>
