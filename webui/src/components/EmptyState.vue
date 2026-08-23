<script setup lang="ts">
import type { Component } from "vue";
import type { HTMLAttributes } from "vue";
import { cn } from "@/lib/utils";

const props = defineProps<{
  title?: string;
  message?: string;
  icon?: Component;
  class?: HTMLAttributes["class"];
}>();
</script>

<template>
  <div
    :class="
      cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-12 text-center',
        props.class,
      )
    "
  >
    <div
      v-if="icon"
      class="flex size-11 items-center justify-center rounded-full bg-muted"
    >
      <component
        :is="icon"
        class="size-5 text-muted-foreground"
        aria-hidden="true"
      />
    </div>
    <p v-if="title" class="text-sm font-medium">{{ title }}</p>
    <p v-if="message" class="max-w-sm text-sm text-muted-foreground">
      {{ message }}
    </p>
    <div v-if="$slots.default" class="mt-2">
      <slot />
    </div>
  </div>
</template>
