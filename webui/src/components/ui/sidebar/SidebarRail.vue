<script setup lang="ts">
import type { HTMLAttributes } from "vue";
import { ref } from "vue";
import { cn } from "@/lib/utils";
import { useSidebar } from "./utils";

const props = defineProps<{
  class?: HTMLAttributes["class"];
}>();

const { toggleSidebar, isMobile, state, sidebarWidth, setSidebarWidth } =
  useSidebar();

const minWidth = 224;
const maxWidth = 384;
const dragging = ref(false);
let startX = 0;
let startWidth = 0;
let moved = false;

function onPointerDown(e: PointerEvent) {
  if (isMobile.value || state.value !== "expanded") return;
  moved = false;
  startX = e.clientX;
  startWidth = sidebarWidth.value;
  dragging.value = true;
  document.documentElement.classList.add("sidebar-resizing");
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return;
  const dx = e.clientX - startX;
  if (Math.abs(dx) > 4) moved = true;
  const next = Math.min(maxWidth, Math.max(minWidth, startWidth + dx));
  setSidebarWidth(next);
}

function onPointerUp(e: PointerEvent) {
  if (!dragging.value) return;
  dragging.value = false;
  document.documentElement.classList.remove("sidebar-resizing");
  try {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
  } catch {
    // already released
  }
}

function onClick() {
  if (moved) {
    moved = false;
    return;
  }
  toggleSidebar();
}
</script>

<template>
  <button
    data-sidebar="rail"
    data-slot="sidebar-rail"
    aria-label="Toggle Sidebar"
    :tabindex="-1"
    title="Toggle Sidebar"
    :class="
      cn(
        'hover:after:bg-sidebar-border absolute inset-y-0 z-20 hidden w-4 -translate-x-1/2 transition-all ease-linear group-data-[side=left]:-right-4 group-data-[side=right]:left-0 after:absolute after:inset-y-0 after:left-1/2 after:w-0.5 sm:flex',
        'in-data-[side=left]:cursor-w-resize in-data-[side=right]:cursor-e-resize touch-none select-none',
        '[[data-side=left][data-state=collapsed]_&]:cursor-e-resize [[data-side=right][data-state=collapsed]_&]:cursor-w-resize',
        'hover:group-data-[collapsible=offcanvas]:bg-sidebar group-data-[collapsible=offcanvas]:translate-x-0 group-data-[collapsible=offcanvas]:after:left-full',
        '[[data-side=left][data-collapsible=offcanvas]_&]:-right-2',
        '[[data-side=right][data-collapsible=offcanvas]_&]:-left-2',
        props.class,
      )
    "
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @click="onClick"
  >
    <slot />
  </button>
</template>
