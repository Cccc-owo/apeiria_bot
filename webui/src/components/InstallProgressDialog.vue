<script setup lang="ts">
import { ref, watch, onUnmounted } from "vue";
import { Loader, Terminal } from "@lucide/vue";
import { useI18n } from "vue-i18n";
import { createSseClient } from "@/lib/sse";
import { useAuthStore } from "@/stores/auth";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { TaskEvent } from "@/types";

const props = defineProps<{
  open: boolean;
  taskId: string | null;
  title: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const auth = useAuthStore();
const { t } = useI18n();
const lines = ref<string[]>([]);
const status = ref<"running" | "done" | "error" | "cancelling" | "cancelled">(
  "running",
);
const errorMsg = ref("");
let sse: ReturnType<typeof createSseClient> | null = null;

function appendLine(line: string | undefined) {
  if (line) lines.value.push(line);
}

function startStream(taskId: string) {
  lines.value = [];
  status.value = "running";
  errorMsg.value = "";

  sse = createSseClient(
    `/api/tasks/${taskId}/stream`,
    auth.token ?? "",
    (data) => {
      try {
        const event: TaskEvent = JSON.parse(data);
        if (event.type === "stage") {
          appendLine(event.line);
        } else if (event.type === "output") {
          appendLine(event.text);
        } else if (event.type === "done") {
          status.value = "done";
        } else if (event.type === "error") {
          status.value = "error";
          errorMsg.value = event.message ?? t("progress.failed");
        } else if (event.type === "cancelled") {
          status.value = "cancelled";
          errorMsg.value = event.message ?? "";
        }
      } catch {
        lines.value.push(data);
      }
    },
  );
}

function stopStream() {
  sse?.close();
  sse = null;
}

async function handleCancel() {
  if (!props.taskId || status.value !== "running") return;
  status.value = "cancelling";
  try {
    await api.tasks.cancel(props.taskId);
  } catch {
    // The server may already have finished; the stream will settle the state.
  }
}

function handleClose() {
  stopStream();
  emit("close");
}

watch(
  () => props.taskId,
  (newId) => {
    stopStream();
    if (newId && props.open) {
      startStream(newId);
    }
  },
);

watch(
  () => props.open,
  (open) => {
    if (!open) {
      stopStream();
    } else if (props.taskId) {
      startStream(props.taskId);
    }
  },
);

onUnmounted(() => stopStream());
</script>

<template>
  <Dialog :open="open" @update:open="(v) => !v && handleClose()">
    <DialogContent
      class="max-w-lg h-[min(72vh,600px)] min-h-[320px] flex flex-col overflow-hidden"
      :show-close-button="
        status === 'done' || status === 'error' || status === 'cancelled'
      "
    >
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Terminal class="size-4" />
          {{ title }}
        </DialogTitle>
        <DialogDescription v-if="status === 'running'">
          {{ $t("progress.installing") }}
        </DialogDescription>
        <DialogDescription v-else-if="status === 'done'">
          {{ $t("progress.done") }}
        </DialogDescription>
        <DialogDescription v-else-if="status === 'cancelling'">
          {{ $t("progress.cancelling") }}
        </DialogDescription>
        <DialogDescription v-else-if="status === 'cancelled'">
          {{ $t("progress.cancelled") }}
        </DialogDescription>
        <DialogDescription v-else>
          {{ $t("progress.failed") }}
        </DialogDescription>
      </DialogHeader>

      <ScrollArea class="flex-1 min-h-0 overflow-hidden rounded-md border bg-black p-3">
        <pre
          class="font-mono text-xs text-green-400 whitespace-pre-wrap break-all leading-relaxed"
        ><template v-for="(line, i) in lines" :key="i">{{ line + '\n' }}</template><span
            v-if="status === 'running' || status === 'cancelling'"
            class="inline-block w-3 h-4 bg-green-400 animate-pulse align-middle ml-0.5"
          >&nbsp;</span><span v-if="status === 'error'" class="text-red-400">{{ errorMsg }}</span><span
            v-if="status === 'cancelled'" class="text-yellow-400"
          >{{ errorMsg }}</span></pre>
      </ScrollArea>

      <DialogFooter>
        <div
          v-if="status === 'running' || status === 'cancelling'"
          class="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <Loader class="size-4 animate-spin" />
          {{
            status === "cancelling"
              ? $t("progress.cancelling")
              : $t("progress.running")
          }}
        </div>
        <Button
          v-if="status === 'running'"
          variant="destructive"
          @click="handleCancel"
        >
          {{ $t("common.cancel") }}
        </Button>
        <Button
          v-if="status === 'done' || status === 'error' || status === 'cancelled'"
          variant="outline"
          @click="handleClose"
        >
          {{ status === 'done' ? $t('progress.complete') : $t('progress.close') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
