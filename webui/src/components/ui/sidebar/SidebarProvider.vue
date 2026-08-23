<script setup lang="ts">
import type { HTMLAttributes, Ref } from "vue";
import {
  defaultDocument,
  useEventListener,
  useMediaQuery,
  useVModel,
} from "@vueuse/core";
import { TooltipProvider } from "reka-ui";
import { computed, ref } from "vue";
import { cn } from "@/lib/utils";
import {
  provideSidebarContext,
  SIDEBAR_COOKIE_MAX_AGE,
  SIDEBAR_COOKIE_NAME,
  SIDEBAR_KEYBOARD_SHORTCUT,
  SIDEBAR_WIDTH_DEFAULT,
  SIDEBAR_WIDTH_ICON,
  SIDEBAR_WIDTH_MAX,
  SIDEBAR_WIDTH_MIN,
  SIDEBAR_WIDTH_STORAGE,
} from "./utils";

function clampWidth(value: number): number {
  return Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, value));
}

function readStoredWidth(): number {
  const raw = Number(
    defaultDocument?.defaultView?.localStorage?.getItem(SIDEBAR_WIDTH_STORAGE),
  );
  if (Number.isFinite(raw) && raw > 0) return clampWidth(raw);
  return SIDEBAR_WIDTH_DEFAULT;
}

const props = withDefaults(
  defineProps<{
    defaultOpen?: boolean;
    open?: boolean;
    class?: HTMLAttributes["class"];
  }>(),
  {
    defaultOpen: !defaultDocument?.cookie.includes(
      `${SIDEBAR_COOKIE_NAME}=false`,
    ),
    open: undefined,
  },
);

const emits = defineEmits<{
  "update:open": [open: boolean];
}>();

const isMobile = useMediaQuery("(max-width: 768px)");
const openMobile = ref(false);

const open = useVModel(props, "open", emits, {
  defaultValue: props.defaultOpen ?? false,
  passive: (props.open === undefined) as false,
}) as Ref<boolean>;

function setOpen(value: boolean) {
  open.value = value; // emits('update:open', value)

  // This sets the cookie to keep the sidebar state.
  document.cookie = `${SIDEBAR_COOKIE_NAME}=${open.value}; path=/; max-age=${SIDEBAR_COOKIE_MAX_AGE}`;
}

function setOpenMobile(value: boolean) {
  openMobile.value = value;
}

// Helper to toggle the sidebar.
function toggleSidebar() {
  return isMobile.value
    ? setOpenMobile(!openMobile.value)
    : setOpen(!open.value);
}

useEventListener("keydown", (event: KeyboardEvent) => {
  if (
    event.key === SIDEBAR_KEYBOARD_SHORTCUT &&
    (event.metaKey || event.ctrlKey)
  ) {
    event.preventDefault();
    toggleSidebar();
  }
});

// We add a state so that we can do data-state="expanded" or "collapsed".
// This makes it easier to style the sidebar with Tailwind classes.
const state = computed(() => (open.value ? "expanded" : "collapsed"));

const sidebarWidth = ref(readStoredWidth());
function setSidebarWidth(value: number) {
  sidebarWidth.value = clampWidth(value);
  defaultDocument?.defaultView?.localStorage?.setItem(
    SIDEBAR_WIDTH_STORAGE,
    String(sidebarWidth.value),
  );
}

provideSidebarContext({
  state,
  open,
  setOpen,
  isMobile,
  openMobile,
  setOpenMobile,
  toggleSidebar,
  sidebarWidth,
  setSidebarWidth,
});
</script>

<template>
  <TooltipProvider :delay-duration="0">
    <div
      data-slot="sidebar-wrapper"
      :style="{
        '--sidebar-width': `${sidebarWidth}px`,
        '--sidebar-width-icon': SIDEBAR_WIDTH_ICON,
      }"
      :class="
        cn(
          'group/sidebar-wrapper has-data-[variant=inset]:bg-sidebar flex min-h-svh w-full',
          props.class,
        )
      "
      v-bind="$attrs"
    >
      <slot />
    </div>
  </TooltipProvider>
</template>
