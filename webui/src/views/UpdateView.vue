<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { toast } from "vue-sonner";
import {
  AlertTriangle,
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  GitBranch,
  GitCommit as GitCommitIcon,
  Loader2,
  Tag,
  Terminal,
} from "@lucide/vue";
import { api } from "@/lib/api";
import type { SseClient } from "@/lib/sse";
import ErrorState from "@/components/ErrorState.vue";
import PageHeader from "@/components/PageHeader.vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  GitCommit,
  TaskEvent,
  UpdatePreviewResponse,
  UpdateStatusResponse,
} from "@/types";

const { t } = useI18n();

const status = ref<UpdateStatusResponse | null>(null);
const statusLoading = ref(false);
const statusError = ref("");

const preview = ref<UpdatePreviewResponse | null>(null);
const previewLoading = ref(false);

const PAGE_SIZE = 10;
const commitRows = ref<GitCommit[]>([]);
const commitsTotal = ref(0);
const page = ref(1);
const jumpInput = ref("");

const totalPages = computed(() =>
  Math.max(1, Math.ceil(commitsTotal.value / PAGE_SIZE)),
);
const hasPrev = computed(() => page.value > 1);
const hasNext = computed(() => page.value < totalPages.value);
const hasCommits = computed(() => commitRows.value.length > 0);

const sourceType = ref<"branch" | "tag">("branch");
const selectedRef = ref("");

const executing = ref(false);
const cancelling = ref(false);
const terminalLines = ref<string[]>([]);
const stage = ref("");
const updateFailed = ref(false);
const updateDone = ref(false);
const updateCancelled = ref(false);
const updateTaskId = ref("");
const polling = ref(false);
const terminalEl = ref<HTMLElement | null>(null);
let updateClient: SseClient | null = null;

const confirmOpen = ref(false);
const pendingCommit = ref<string | null>(null);

const hasTrackedChanges = computed(
  () => !!status.value?.has_tracked_changes,
);
const dirtyOnlyUntracked = computed(
  () => !!status.value?.is_dirty && !status.value?.has_tracked_changes,
);

const pendingCommitInfo = computed<GitCommit | null>(() => {
  if (!pendingCommit.value || !preview.value) return null;
  return (
    preview.value.commits.find((c) => c.hash === pendingCommit.value) ?? null
  );
});

function requestExecute(commit: string) {
  if (executing.value) return;
  pendingCommit.value = commit;
  confirmOpen.value = true;
}

async function fetchStatus() {
  statusLoading.value = true;
  statusError.value = "";
  try {
    status.value = await api.update.status();
    if (!selectedRef.value && status.value) {
      selectedRef.value = status.value.branch;
    }
  } catch (err: unknown) {
    statusError.value = (err as Error).message;
  } finally {
    statusLoading.value = false;
  }
}

async function fetchPage(target: number) {
  const data = await api.update.preview(
    selectedRef.value,
    sourceType.value,
    (target - 1) * PAGE_SIZE,
    PAGE_SIZE,
  );
  preview.value = data;
  commitRows.value = data.commits;
  commitsTotal.value = data.total;
  page.value = target;
}

async function loadPage(target: number) {
  if (!selectedRef.value) return;
  previewLoading.value = true;
  try {
    await fetchPage(target);
  } catch {
    // Keep the current page rows; the paginator lets the user retry.
  } finally {
    previewLoading.value = false;
  }
}

async function fetchPreview() {
  if (!selectedRef.value) return;
  preview.value = null;
  commitRows.value = [];
  commitsTotal.value = 0;
  page.value = 1;
  await loadPage(1);
}

function goToPage(target: number) {
  if (previewLoading.value || target < 1 || target > totalPages.value) return;
  if (target === page.value) return;
  void loadPage(target);
}

function goFirst() {
  if (page.value !== 1) void loadPage(1);
}

function goLast() {
  if (page.value !== totalPages.value) void loadPage(totalPages.value);
}

async function jumpByHash(hash: string) {
  if (!selectedRef.value || previewLoading.value) return;
  try {
    const res = await api.update.locate(
      selectedRef.value,
      hash,
      sourceType.value,
      PAGE_SIZE,
    );
    goToPage(res.page);
    jumpInput.value = "";
  } catch {
    toast.error(t("update.commitNotFound"));
  }
}

function onJump() {
  const value = jumpInput.value.trim();
  if (!value || previewLoading.value) return;
  const asPage = Number(value);
  if (Number.isInteger(asPage) && asPage >= 1) {
    goToPage(asPage);
    return;
  }
  void jumpByHash(value);
}

watch(selectedRef, () => fetchPreview());
watch(sourceType, () => {
  if (status.value) {
    if (
      sourceType.value === "branch" &&
      status.value.available_branches.length > 0
    ) {
      selectedRef.value = status.value.available_branches[0];
    } else if (
      sourceType.value === "tag" &&
      status.value.available_tags.length > 0
    ) {
      selectedRef.value = status.value.available_tags[0];
    }
  }
});

const dirtyFiles = computed(() => {
  if (!status.value?.dirty_files) return [];
  return status.value.dirty_files;
});

const fetchWarning = computed(
  () => status.value?.fetch_warning || preview.value?.fetch_warning || "",
);

const sourceOptions = computed(() => {
  if (!status.value) return [];
  return sourceType.value === "branch"
    ? status.value.available_branches
    : status.value.available_tags;
});

function canExecuteRow(hash: string): boolean {
  return !!(
    status.value &&
    !executing.value &&
    !updateDone.value &&
    hash !== status.value.commit_hash
  );
}

function buttonLabel(commit: GitCommit): string {
  switch (commit.direction) {
    case "ahead":
      return t("update.execute");
    case "behind":
      return t("update.rollbackTo");
    default:
      return "";
  }
}

function stageLabel(s: string): string {
  const map: Record<string, string> = {
    checkout: t("update.checkout"),
    pull: t("update.pull"),
    sync: t("update.sync"),
    rollback: t("update.rollback"),
    stash: t("update.stash"),
    error: t("update.failed"),
    done: t("update.success"),
  };
  return map[s] ?? s;
}

async function scrollTerminal() {
  await nextTick();
  if (terminalEl.value) {
    terminalEl.value.scrollTop = terminalEl.value.scrollHeight;
  }
}

async function executeUpdate(commit: string, dirtyStrategy: "stash" | "discard" | "block") {
  if (!selectedRef.value || executing.value) return;
  executing.value = true;
  cancelling.value = false;
  updateFailed.value = false;
  updateDone.value = false;
  updateCancelled.value = false;
  updateTaskId.value = "";
  terminalLines.value = [];
  stage.value = "";

  updateClient = api.update.execute(
    selectedRef.value,
    commit,
    sourceType.value,
    (data) => {
      try {
        const event: TaskEvent = JSON.parse(data);
        if (event.type === "task") {
          updateTaskId.value = event.task_id ?? "";
        } else if (event.type === "stage") {
          stage.value = event.stage ?? "";
          if (event.line) terminalLines.value.push(event.line);
          void scrollTerminal();
          if (event.stage === "error") updateFailed.value = true;
          if (event.stage === "done") {
            updateDone.value = true;
            pollUntilUp();
          }
        } else if (event.type === "output") {
          if (event.text) terminalLines.value.push(event.text);
          void scrollTerminal();
        } else if (event.type === "error") {
          updateFailed.value = true;
          if (event.message) terminalLines.value.push(event.message);
          void scrollTerminal();
        } else if (event.type === "cancelled") {
          updateCancelled.value = true;
          if (event.message) terminalLines.value.push(event.message);
          void scrollTerminal();
        }
      } catch {
        // skip unparseable
      }
    },
    (err) => {
      terminalLines.value.push(`Connection lost: ${err.message}`);
      updateFailed.value = true;
    },
    dirtyStrategy,
  );

  await updateClient.done;
  executing.value = false;
  cancelling.value = false;
  updateClient = null;
}

function onConfirmOpen(v: boolean) {
  confirmOpen.value = v;
  if (!v) pendingCommit.value = null;
}

function confirmStashAndRun() {
  const commit = pendingCommit.value;
  confirmOpen.value = false;
  pendingCommit.value = null;
  if (commit) void executeUpdate(commit, "stash");
}

function confirmDiscardAndRun() {
  const commit = pendingCommit.value;
  confirmOpen.value = false;
  pendingCommit.value = null;
  if (commit) void executeUpdate(commit, "discard");
}

function confirmRun() {
  const commit = pendingCommit.value;
  confirmOpen.value = false;
  pendingCommit.value = null;
  // No tracked changes: proceed directly; untracked files are left untouched by
  // `git reset --hard`, so "discard" here simply means "run without stashing".
  if (commit) void executeUpdate(commit, "discard");
}

function pollUntilUp() {
  polling.value = true;
  let attempts = 0;
  const max = 60;
  const interval = setInterval(async () => {
    attempts++;
    try {
      await api.status.get();
      clearInterval(interval);
      toast.success(t("update.success"));
      polling.value = false;
      fetchStatus();
    } catch {
      if (attempts >= max) {
        clearInterval(interval);
        polling.value = false;
        toast.error(t("dashboard.restartTimeout"));
      }
    }
  }, 2000);
}

async function cancelUpdate() {
  if (updateTaskId.value && executing.value && !cancelling.value) {
    cancelling.value = true;
    try {
      await api.tasks.cancel(updateTaskId.value);
    } catch {
      // If cancel request failed, closing the stream still detaches the UI.
    }
  }
  updateClient?.close();
  updateClient = null;
  executing.value = false;
  cancelling.value = false;
}

onUnmounted(() => {
  cancelUpdate();
});

function isCurrentCommit(hash: string): boolean {
  return status.value?.commit_hash === hash;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  return dateStr.slice(0, 10) + " " + dateStr.slice(11, 16);
}

fetchStatus();
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col p-6 lg:p-8">
    <PageHeader
      :title="t('update.title')"
      :subtitle="t('update.subtitle')"
      class="flex-none"
    />

    <ErrorState
      v-if="statusError"
      :title="$t('error.loadFailed')"
      :description="statusError"
      @retry="fetchStatus()"
    />

    <div v-else class="flex min-h-0 flex-1 flex-col gap-5">
      <!-- Remote refresh warning -->
      <div
        v-if="fetchWarning"
        class="flex items-start gap-2 rounded-md border border-yellow-600/40 bg-yellow-600/10 p-3"
      >
        <AlertTriangle class="mt-0.5 size-4 shrink-0 text-yellow-500" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-yellow-500">
            {{ t("update.fetchWarning") }}
          </p>
          <p class="mt-1 text-xs text-yellow-400/80">{{ fetchWarning }}</p>
        </div>
      </div>

      <!-- Status Card -->
      <Card class="flex-none">
        <CardHeader>
          <CardTitle class="flex items-center gap-2 text-base">
            <GitBranch class="size-4" />
            {{ t("update.currentBranch") }}
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div v-if="statusLoading" class="space-y-2">
            <Skeleton class="h-5 w-48" />
            <Skeleton class="h-4 w-96" />
          </div>
          <template v-else-if="status">
            <div class="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{{ status.branch }}</Badge>
              <GitCommitIcon class="size-3.5 text-muted-foreground" />
              <code class="text-sm text-muted-foreground">{{
                status.commit_hash
              }}</code>
              <span class="text-sm text-muted-foreground truncate max-w-md">
                {{ status.commit_message }}
              </span>
            </div>

            <div
              v-if="status.is_dirty"
              class="flex items-start gap-2 rounded-md border border-yellow-600/40 bg-yellow-600/10 p-3"
            >
              <AlertTriangle class="mt-0.5 size-4 shrink-0 text-yellow-500" />
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium text-yellow-500">
                  {{
                    hasTrackedChanges
                      ? t("update.dirtyWarning")
                      : t("update.untrackedOnly")
                  }}
                </p>
                <p
                  v-if="hasTrackedChanges"
                  class="mt-1 text-xs text-yellow-500/80"
                >
                  {{ t("update.dirtyHint") }}
                </p>
                <p class="mt-1 text-xs font-medium text-yellow-400/80">
                  {{ t("update.dirtyFiles") }}:
                </p>
                <ul class="mt-1 list-inside list-disc space-y-0.5">
                  <li
                    v-for="f in dirtyFiles"
                    :key="f"
                    class="truncate font-mono text-xs text-yellow-300/80"
                  >
                    {{ f }}
                  </li>
                </ul>
              </div>
            </div>
          </template>
        </CardContent>
      </Card>

      <!-- Source Selector (Branch / Tag) -->
      <Card class="flex-none">
        <CardHeader class="pb-3">
          <Tabs
            :model-value="sourceType"
            @update:model-value="sourceType = $event as 'branch' | 'tag'"
          >
            <TabsList>
              <TabsTrigger value="branch" :disabled="executing">
                <GitBranch class="mr-1.5 size-3.5" />
                {{ t("update.branchTab") }}
              </TabsTrigger>
              <TabsTrigger
                value="tag"
                :disabled="executing || !status?.available_tags?.length"
              >
                <Tag class="mr-1.5 size-3.5" />
                {{ t("update.tagTab") }}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="flex items-center gap-3">
            <label class="text-sm font-medium text-muted-foreground shrink-0">
              {{
                sourceType === "branch"
                  ? t("update.selectBranch")
                  : t("update.selectTag")
              }}:
            </label>
            <template v-if="statusLoading">
              <Skeleton class="h-9 w-56" />
            </template>
            <Select
              v-else-if="sourceOptions.length > 0"
              v-model="selectedRef"
              :disabled="executing"
            >
              <SelectTrigger class="w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="opt in sourceOptions"
                  :key="opt"
                  :value="opt"
                >
                  {{ opt }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p v-else class="text-sm text-muted-foreground">
              {{ t("update.noUpdate") }}
            </p>
          </div>

          <!-- Commit List Table -->
          <div v-if="previewLoading && commitRows.length === 0" class="space-y-2">
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-3/4" />
            <Skeleton class="h-4 w-5/6" />
          </div>
          <template v-else-if="preview && hasCommits">
            <p class="text-sm font-medium text-muted-foreground">
              {{ t("update.selectCommit") }} ({{ commitsTotal }})
            </p>
            <div
              v-if="
                preview.has_diverged || preview.local_only_commits.length > 0
              "
              class="flex items-start gap-2 rounded-md border border-yellow-600/40 bg-yellow-600/10 p-3"
            >
              <AlertTriangle class="mt-0.5 size-4 shrink-0 text-yellow-500" />
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium text-yellow-500">
                  {{ t("update.divergedWarning") }}
                </p>
                <ul
                  v-if="preview.local_only_commits.length > 0"
                  class="mt-1 list-inside list-disc space-y-0.5"
                >
                  <li
                    v-for="c in preview.local_only_commits"
                    :key="c.hash"
                    class="truncate font-mono text-xs text-yellow-300/80"
                  >
                    {{ c.hash }} {{ c.message }}
                  </li>
                </ul>
              </div>
            </div>
            <Table class="max-h-80 overflow-auto rounded-md border">
              <TableHeader
                class="sticky top-0 z-10 bg-muted"
              >
                  <TableRow class="hover:bg-transparent">
                    <TableHead class="px-3 py-2">Commit</TableHead>
                    <TableHead class="px-3 py-2">
                      {{ t("update.commitMessage") }}
                    </TableHead>
                    <TableHead class="hidden px-3 py-2 sm:table-cell">
                      {{ t("update.commitAuthor") }}
                    </TableHead>
                    <TableHead class="hidden px-3 py-2 sm:table-cell">
                      {{ t("update.commitDate") }}
                    </TableHead>
                    <TableHead class="w-24 px-3 py-2 text-center">
                      {{ t("update.action") }}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow
                    v-for="c in commitRows"
                    :key="c.hash"
                    :class="
                      isCurrentCommit(c.hash) ? 'bg-emerald-500/5' : ''
                    "
                  >
                    <TableCell class="whitespace-nowrap px-3 py-2 font-mono">
                      <code>{{ c.hash }}</code>
                      <Badge
                        v-if="isCurrentCommit(c.hash)"
                        variant="secondary"
                        class="ml-1 text-[0.6rem]"
                      >
                        {{ t("update.currentLabel") }}
                      </Badge>
                    </TableCell>
                    <TableCell class="max-w-64 truncate px-3 py-2">
                      {{ c.message }}
                    </TableCell>
                    <TableCell
                      class="hidden px-3 py-2 text-muted-foreground sm:table-cell"
                    >
                      {{ c.author }}
                    </TableCell>
                    <TableCell
                      class="hidden whitespace-nowrap px-3 py-2 text-muted-foreground sm:table-cell"
                    >
                      {{ formatDate(c.date) }}
                    </TableCell>
                    <TableCell class="px-2 py-1 text-center">
                      <Button
                        v-if="!isCurrentCommit(c.hash)"
                        size="sm"
                        variant="outline"
                        :disabled="!canExecuteRow(c.hash)"
                        @click.stop="requestExecute(c.hash)"
                      >
                        {{ buttonLabel(c) }}
                      </Button>
                      <span v-else class="text-xs text-muted-foreground">—</span>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <div
                v-if="totalPages > 1"
                class="mt-2 flex flex-wrap items-center justify-between gap-2"
              >
                <div class="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    :aria-label="t('update.firstPage')"
                    :disabled="!hasPrev || previewLoading"
                    @click="goFirst"
                  >
                    <ChevronFirst class="size-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    :aria-label="t('update.prevPage')"
                    :disabled="!hasPrev || previewLoading"
                    @click="goToPage(page - 1)"
                  >
                    <ChevronLeft class="size-4" />
                  </Button>
                  <span
                    class="min-w-24 text-center text-sm text-muted-foreground"
                  >
                    <Loader2
                      v-if="previewLoading"
                      class="mr-1 inline-block size-3.5 animate-spin"
                    />
                    {{ t("update.pageIndicator", { page, total: totalPages }) }}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    :aria-label="t('update.nextPage')"
                    :disabled="!hasNext || previewLoading"
                    @click="goToPage(page + 1)"
                  >
                    <ChevronRight class="size-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    :aria-label="t('update.lastPage')"
                    :disabled="!hasNext || previewLoading"
                    @click="goLast"
                  >
                    <ChevronLast class="size-4" />
                  </Button>
                </div>
                <div class="flex items-center gap-2">
                  <Input
                    v-model="jumpInput"
                    class="h-8 w-44"
                    :placeholder="t('update.jumpPlaceholder')"
                    @keydown.enter="onJump"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    :disabled="previewLoading || !jumpInput.trim()"
                    @click="onJump"
                  >
                    {{ t("update.jump") }}
                  </Button>
                </div>
              </div>
          </template>
          <p v-else-if="preview" class="text-sm text-muted-foreground">
            {{ t("update.noCommits") }}
          </p>
        </CardContent>
      </Card>

      <!-- Execute Controls -->
      <div class="flex-none">
        <Button
          v-if="executing"
          variant="destructive"
          :disabled="cancelling"
          @click="cancelUpdate()"
        >
          {{ cancelling ? t("update.cancelling") : $t("common.cancel") }}
        </Button>
        <Button v-else-if="polling" disabled>
          <Loader2 class="mr-1.5 size-4 animate-spin" />
          {{ t("update.reconnecting") }}
        </Button>
      </div>

      <!-- Terminal Output -->
      <Card
        v-if="executing || terminalLines.length > 0"
        class="flex min-h-0 flex-1 flex-col"
      >
        <CardHeader class="pb-2">
          <CardTitle class="flex items-center gap-2 text-base">
            <Terminal class="size-4" />
            <span v-if="stage">{{ stageLabel(stage) }}</span>
            <Loader2
              v-if="executing || cancelling"
              class="size-4 animate-spin text-muted-foreground"
            />
          </CardTitle>
        </CardHeader>
        <CardContent class="min-h-0 flex-1 overflow-hidden p-0">
          <div
            ref="terminalEl"
            class="h-full overflow-auto rounded-b-lg bg-zinc-950 p-4 font-mono text-xs leading-relaxed"
          >
            <template v-for="(line, i) in terminalLines" :key="i">
              <div class="text-zinc-300">{{ line }}</div>
            </template>
            <div
              v-if="(executing || cancelling) && terminalLines.length > 0"
              class="mt-1 inline-block h-4 w-2 animate-pulse bg-emerald-400"
            />
          </div>
        </CardContent>
      </Card>

      <!-- Post-update -->
      <div
        v-if="updateDone || updateCancelled"
        class="flex items-center gap-2 text-sm text-muted-foreground"
      >
        <Loader2 v-if="polling" class="size-4 animate-spin text-emerald-500" />
        <span v-if="polling">{{ t("update.reconnecting") }}</span>
        <span
          v-else-if="updateCancelled"
          class="text-yellow-500"
        >{{ t("update.cancelled") }}</span>
        <span v-else class="text-emerald-500">{{ t("update.success") }}</span>
      </div>
    </div>

    <!-- Dangerous-action confirmation -->
    <Dialog :open="confirmOpen" @update:open="onConfirmOpen">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t("update.confirmTitle") }}</DialogTitle>
          <DialogDescription>
            <template v-if="pendingCommitInfo">
              <span class="font-medium">{{ buttonLabel(pendingCommitInfo) }}</span>
              <code class="ml-1 font-mono text-xs">{{ pendingCommitInfo.hash }}</code>
              <span class="ml-1 text-xs text-muted-foreground">
                {{ pendingCommitInfo.message }}
              </span>
            </template>
          </DialogDescription>
        </DialogHeader>

        <div
          v-if="hasTrackedChanges"
          class="flex items-start gap-2 rounded-md border border-yellow-600/40 bg-yellow-600/10 p-3"
        >
          <AlertTriangle class="mt-0.5 size-4 shrink-0 text-yellow-500" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-yellow-500">
              {{ t("update.dirtyConfirmMsg") }}
            </p>
            <p class="mt-1 text-xs text-yellow-500/80">
              {{ t("update.dirtyHint") }}
            </p>
          </div>
        </div>
        <div
          v-else-if="dirtyOnlyUntracked"
          class="flex items-start gap-2 rounded-md border border-yellow-600/40 bg-yellow-600/10 p-3"
        >
          <AlertTriangle class="mt-0.5 size-4 shrink-0 text-yellow-500" />
          <p class="text-sm text-yellow-500">{{ t("update.untrackedNote") }}</p>
        </div>

        <DialogFooter>
          <template v-if="hasTrackedChanges">
            <Button variant="ghost" @click="confirmOpen = false">
              {{ $t("common.cancel") }}
            </Button>
            <Button variant="destructive" @click="confirmDiscardAndRun">
              {{ t("update.discardContinue") }}
            </Button>
            <Button @click="confirmStashAndRun">
              {{ t("update.stashContinue") }}
            </Button>
          </template>
          <template v-else>
            <Button variant="ghost" @click="confirmOpen = false">
              {{ $t("common.cancel") }}
            </Button>
            <Button @click="confirmRun">
              {{ t("update.confirmContinue") }}
            </Button>
          </template>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
