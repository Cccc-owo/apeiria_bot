<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import loader from "@monaco-editor/loader";
import { AlertTriangle, Loader2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type * as Monaco from "monaco-editor";

const props = defineProps<{
  modelValue: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

// CDN 加载超时：超过该时长仍无法拿到 Monaco 即降级为纯文本编辑，
// 避免在弱网 / CDN 不可达时无限转圈。
const LOAD_TIMEOUT_MS = 12000;

const containerRef = ref<HTMLElement | null>(null);
const ready = ref(false);
const failed = ref(false);
const fallbackText = ref("");

let editor: Monaco.editor.IStandaloneCodeEditor | null = null;
let observer: MutationObserver | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let timeoutTimer: ReturnType<typeof setTimeout> | null = null;

function createEditor(monaco: typeof Monaco) {
  if (!containerRef.value) return;

  editor = monaco.editor.create(containerRef.value, {
    value: props.modelValue,
    language: "yaml",
    theme: document.documentElement.classList.contains("dark")
      ? "vs-dark"
      : "vs",
    minimap: { enabled: false },
    fontSize: 13,
    tabSize: 2,
    automaticLayout: true,
    scrollBeyondLastLine: false,
    lineNumbers: "on",
    renderWhitespace: "selection",
  });

  editor!.onDidChangeModelContent(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      emit("update:modelValue", editor!.getValue());
    }, 500);
  });

  observer = new MutationObserver(() => {
    if (editor) {
      monaco.editor.setTheme(
        document.documentElement.classList.contains("dark") ? "vs-dark" : "vs",
      );
    }
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });

  ready.value = true;
}

async function initMonaco() {
  failed.value = false;
  timeoutTimer = setTimeout(() => {
    failed.value = true;
  }, LOAD_TIMEOUT_MS);

  try {
    const monaco = await loader.init();
    if (timeoutTimer) clearTimeout(timeoutTimer);
    if (failed.value) return; // 已超时，放弃挂载
    createEditor(monaco);
  } catch {
    if (timeoutTimer) clearTimeout(timeoutTimer);
    failed.value = true;
  }
}

function retry() {
  void initMonaco();
}

function onFallbackInput(value: string | number) {
  const v = String(value);
  fallbackText.value = v;
  emit("update:modelValue", v);
}

onMounted(() => {
  fallbackText.value = props.modelValue;
  void initMonaco();
});

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer);
  if (timeoutTimer) clearTimeout(timeoutTimer);
  observer?.disconnect();
  editor?.dispose();
});

watch(
  () => props.modelValue,
  (newVal) => {
    if (editor && newVal !== editor.getValue()) {
      editor.setValue(newVal);
    }
    if (failed.value && newVal !== fallbackText.value) {
      fallbackText.value = newVal;
    }
  },
);
</script>

<template>
  <div
    class="relative h-full min-h-[200px] w-full overflow-hidden rounded-md border"
  >
    <div ref="containerRef" class="h-full min-h-[200px] w-full" />

    <div
      v-if="!ready && !failed"
      class="absolute inset-0 flex items-center justify-center bg-background"
    >
      <Loader2 class="size-8 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="failed" class="absolute inset-0 flex flex-col bg-background">
      <div
        class="flex items-center gap-2 border-b bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
      >
        <AlertTriangle class="size-3.5 shrink-0 text-amber-500" />
        <span class="truncate">{{ $t("config.editorFallback") }}</span>
        <Button
          variant="ghost"
          size="sm"
          class="ml-auto h-6 px-2 text-xs"
          @click="retry"
        >
          {{ $t("common.retry") }}
        </Button>
      </div>
      <Textarea
        :model-value="fallbackText"
        class="min-h-0 flex-1 resize-none rounded-none border-0 font-mono text-xs leading-relaxed focus-visible:ring-0"
        spellcheck="false"
        @update:model-value="onFallbackInput"
      />
    </div>
  </div>
</template>
