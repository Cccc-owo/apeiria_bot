<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useMediaQuery } from "@vueuse/core";
import {
  ArrowLeft,
  ImagePlus,
  MessageCircle,
  Plus,
  Send,
  Trash2,
  UserPlus,
  Users,
  X,
} from "@lucide/vue";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useWebchat } from "@/composables/useWebchat";
import { cn } from "@/lib/utils";
import type { WebchatConversation, WebchatMessage } from "@/types";
import ImageLightbox from "@/components/webchat/ImageLightbox.vue";

const {
  store,
  connected,
  conversations,
  currentConversation,
  activeMessages,
  send,
  clear,
  deleteMessage,
  selectConversation,
  switchUser,
  addUser,
  removeUser,
  addGroup,
  removeGroup,
} = useWebchat();

const draft = ref("");
const pendingImage = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const scrollEl = ref<HTMLElement | null>(null);
const clearOpen = ref(false);
const addUserOpen = ref(false);
const addGroupOpen = ref(false);
const newUserId = ref("");
const newUserName = ref("");
const newGroupId = ref("");
const newGroupName = ref("");
const lightboxOpen = ref(false);
const lightboxIndex = ref(0);

const isMobile = useMediaQuery("(max-width: 768px)");
const mobilePane = ref<"list" | "chat">("list");

function openConversation(c: WebchatConversation) {
  selectConversation(c);
  if (isMobile.value) mobilePane.value = "chat";
}

function backToList() {
  mobilePane.value = "list";
}

interface ImageEntry {
  url: string;
  msgId: string;
  segIdx: number;
}

const imageList = computed<ImageEntry[]>(() => {
  const result: ImageEntry[] = [];
  for (const m of activeMessages.value) {
    for (let i = 0; i < m.segments.length; i++) {
      const seg = m.segments[i];
      if (seg.type === "image") {
        result.push({ url: seg.url, msgId: m.id, segIdx: i });
      }
    }
  }
  return result;
});

function openLightbox(idx: number) {
  lightboxIndex.value = idx;
  lightboxOpen.value = true;
}

function findImageIndex(msgId: string, segIdx: number): number {
  return imageList.value.findIndex((e) => e.msgId === msgId && e.segIdx === segIdx);
}

const currentUser = computed({
  get: () => store.currentUserId,
  set: (v: string) => switchUser(v),
});

function scrollToBottom() {
  const el = scrollEl.value;
  if (el) el.scrollTop = el.scrollHeight;
}

watch(
  () => [activeMessages.value.length, store.currentConversationKey],
  () => void nextTick(scrollToBottom),
);

function onSend() {
  if (!draft.value.trim()) return;
  send(draft.value, pendingImage.value ?? undefined);
  draft.value = "";
  pendingImage.value = null;
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    onSend();
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = () => (pendingImage.value = reader.result as string);
    reader.readAsDataURL(file);
  }
  input.value = "";
}

function onClear() {
  clear();
  clearOpen.value = false;
}

function onAddUser() {
  addUser(newUserId.value, newUserName.value);
  newUserId.value = "";
  newUserName.value = "";
  addUserOpen.value = false;
}

function onAddGroup() {
  addGroup(newGroupId.value, newGroupName.value);
  newGroupId.value = "";
  newGroupName.value = "";
  addGroupOpen.value = false;
}

function isMine(m: WebchatMessage): boolean {
  return m.role === "user" && m.user_id === store.currentUserId;
}

function colorFor(id?: string | null): {
  backgroundColor: string;
  color: string;
} {
  const s = id ?? "";
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) % 360;
  }
  const hue = Math.abs(hash);
  return {
    backgroundColor: `hsl(${hue} 60% 88%)`,
    color: `hsl(${hue} 45% 32%)`,
  };
}

function senderLabel(m: WebchatMessage): string {
  return m.role === "bot" ? "Bot" : store.userName(m.user_id ?? "");
}

function avatarText(m: WebchatMessage): string {
  return m.role === "bot" ? "B" : (m.user_id ?? "U").slice(0, 1).toUpperCase();
}
</script>

<template>
  <div class="flex h-full min-h-0">
    <aside
      :class="
        cn(
          'flex min-h-0 flex-col border-r bg-card/40',
          isMobile
            ? mobilePane === 'chat'
              ? 'hidden'
              : 'w-full'
            : 'w-60 shrink-0',
        )
      "
    >
      <div class="flex shrink-0 items-center gap-2 border-b p-3">
        <Select v-model="currentUser">
          <SelectTrigger class="flex-1">
            <SelectValue :placeholder="$t('webchat.account')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="u in store.users" :key="u.id" :value="u.id">
              {{ u.name }}
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="icon"
          :aria-label="$t('webchat.addAccount')"
          @click="addUserOpen = true"
        >
          <UserPlus class="size-4" />
        </Button>
        <Button
          v-if="store.users.length > 1"
          variant="outline"
          size="icon"
          :aria-label="$t('webchat.removeAccount')"
          @click="removeUser(store.currentUserId)"
        >
          <Trash2 class="size-4" />
        </Button>
      </div>
      <div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto p-2">
        <div
          v-for="c in conversations"
          :key="c.key"
          role="button"
          tabindex="0"
          :class="
            cn(
              'group flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm',
              c.key === store.currentConversationKey
                ? 'bg-accent text-accent-foreground'
                : 'hover:bg-secondary',
            )
          "
          @click="openConversation(c)"
          @keydown.enter="openConversation(c)"
        >
          <component
            :is="c.type === 'group' ? Users : MessageCircle"
            class="size-4 shrink-0"
          />
          <span class="flex-1 truncate">{{ c.name }}</span>
          <button
            v-if="c.type === 'group'"
            type="button"
            class="opacity-0 transition-opacity group-hover:opacity-100"
            :aria-label="$t('common.delete')"
            @click.stop="removeGroup(c.groupId ?? '')"
          >
            <X class="size-3.5" />
          </button>
        </div>
        <Button
          variant="ghost"
          size="sm"
          class="mt-1 justify-start"
          @click="addGroupOpen = true"
        >
          <Plus class="size-4" />
          {{ $t("webchat.addGroup") }}
        </Button>
      </div>
    </aside>

    <section
      :class="
        cn(
          'flex min-h-0 min-w-0 flex-col p-4 lg:p-6',
          isMobile
            ? mobilePane === 'list'
              ? 'hidden'
              : 'w-full'
            : 'flex-1',
        )
      "
    >
      <div class="mb-3 flex shrink-0 flex-wrap items-center justify-between gap-x-2 gap-y-2">
        <div class="flex min-w-0 flex-1 items-center gap-2">
          <Button
            v-if="isMobile"
            variant="ghost"
            size="icon"
            class="-ml-1 size-8 shrink-0"
            :aria-label="$t('webchat.back')"
            @click="backToList"
          >
            <ArrowLeft class="size-4" />
          </Button>
          <component
            :is="currentConversation?.type === 'group' ? Users : MessageCircle"
            class="size-4 shrink-0 text-muted-foreground"
          />
          <h2 class="truncate text-sm font-medium">
            {{ currentConversation?.name ?? $t("webchat.title") }}
          </h2>
          <Badge variant="secondary" class="max-w-[42vw] shrink-0 truncate">
            {{ $t("webchat.actingAs", { user: store.currentUserId }) }}
          </Badge>
        </div>
        <div class="flex shrink-0 items-center gap-3">
          <span class="flex items-center gap-1.5 text-sm text-muted-foreground">
            <span
              :class="
                cn(
                  'size-2 rounded-full',
                  connected ? 'bg-success' : 'bg-destructive',
                )
              "
            />
            <span class="max-sm:hidden">{{
              connected ? $t("webchat.connected") : $t("webchat.disconnected")
            }}</span>
          </span>
          <Dialog v-model:open="clearOpen">
            <Button variant="outline" size="sm" @click="clearOpen = true">
              <Trash2 class="size-4" />
              {{ $t("webchat.clear") }}
            </Button>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{{ $t("webchat.clearConfirmTitle") }}</DialogTitle>
                <DialogDescription>
                  {{ $t("webchat.clearConfirmDesc") }}
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" @click="clearOpen = false">
                  {{ $t("common.cancel") }}
                </Button>
                <Button variant="destructive" @click="onClear">
                  {{ $t("common.confirm") }}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div
        ref="scrollEl"
        class="flex min-h-0 flex-1 flex-col gap-4 overflow-auto rounded-xl border bg-card p-4"
      >
        <p
          v-if="!activeMessages.length"
          class="py-10 text-center text-sm text-muted-foreground"
        >
          {{ $t("webchat.empty") }}
        </p>
        <div
          v-for="m in activeMessages"
          :key="m.id"
          :class="
            cn(
              'group flex flex-col gap-1',
              isMine(m) ? 'items-end' : 'items-start',
            )
          "
        >
          <span v-if="!isMine(m)" class="pl-10 text-xs text-muted-foreground">
            {{ senderLabel(m) }}
          </span>
          <div
            :class="
              cn(
                'flex max-w-[80%] items-end gap-2',
                isMine(m) ? 'flex-row-reverse' : 'flex-row',
              )
            "
          >
            <Avatar class="size-8 shrink-0">
              <AvatarFallback
                v-if="m.role === 'bot'"
                class="bg-primary/10 text-primary"
              >
                B
              </AvatarFallback>
              <AvatarFallback v-else :style="colorFor(m.user_id)">
                {{ avatarText(m) }}
              </AvatarFallback>
            </Avatar>
            <div
              :class="
                cn(
                  'min-w-0 rounded-lg px-3 py-2 text-sm break-words',
                  isMine(m)
                    ? 'bg-accent text-accent-foreground'
                    : 'bg-secondary text-secondary-foreground',
                )
              "
            >
              <template v-for="(seg, i) in m.segments" :key="i">
                <span v-if="seg.type === 'text'" class="whitespace-pre-wrap">{{
                  seg.text
                }}</span>
                <img
                  v-else-if="seg.type === 'image'"
                  :src="seg.url"
                  alt=""
                  class="max-h-60 max-w-full rounded-md cursor-pointer hover:opacity-90 transition-opacity"
                  @click="openLightbox(findImageIndex(m.id, i))"
                />
                <details v-else class="text-xs">
                  <summary class="cursor-pointer">
                    <Badge variant="secondary">{{ seg.seg_type }}</Badge>
                  </summary>
                  <pre class="mt-1 overflow-auto">{{
                    JSON.stringify(seg.data, null, 2)
                  }}</pre>
                </details>
              </template>
            </div>
          </div>
          <div
            :class="
              cn(
                'flex items-center gap-2 text-xs text-muted-foreground',
                isMine(m) ? 'pr-10' : 'pl-10',
              )
            "
          >
            <span>{{ m.time }}</span>
            <button
              type="button"
              class="opacity-0 transition-opacity group-hover:opacity-100"
              :aria-label="$t('webchat.deleteMessage')"
              @click="deleteMessage(m.id)"
            >
              <Trash2 class="size-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div class="mt-3 flex shrink-0 items-end gap-2">
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          class="hidden"
          @change="onFileChange"
        />
        <Button
          variant="outline"
          size="icon"
          :aria-label="$t('webchat.attachImage')"
          @click="fileInput?.click()"
        >
          <ImagePlus class="size-4" />
        </Button>
        <div class="flex-1">
          <div
            v-if="pendingImage"
            class="mb-2 inline-flex items-center gap-2 rounded-md border bg-muted p-1"
          >
            <img
              :src="pendingImage"
              alt=""
              class="size-12 rounded object-cover"
            />
            <Button
              variant="ghost"
              size="icon"
              :aria-label="$t('common.delete')"
              @click="pendingImage = null"
            >
              <X class="size-4" />
            </Button>
          </div>
          <Textarea
            v-model="draft"
            rows="1"
            :placeholder="$t('webchat.inputPlaceholder')"
            @keydown="onKeydown"
          />
        </div>
        <Button
          :disabled="!connected || !currentConversation || !draft.trim()"
          @click="onSend"
        >
          <Send class="size-4" />
          {{ $t("webchat.send") }}
        </Button>
      </div>
    </section>

    <Dialog v-model:open="addUserOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ $t("webchat.addAccount") }}</DialogTitle>
          <DialogDescription>{{
            $t("webchat.addAccountDesc")
          }}</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <Label for="wc-uid">{{ $t("webchat.userId") }}</Label>
            <Input
              id="wc-uid"
              v-model="newUserId"
              :placeholder="$t('webchat.userIdPlaceholder')"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="wc-uname">{{ $t("webchat.displayName") }}</Label>
            <Input
              id="wc-uname"
              v-model="newUserName"
              :placeholder="$t('webchat.optional')"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="addUserOpen = false">
            {{ $t("common.cancel") }}
          </Button>
          <Button :disabled="!newUserId.trim()" @click="onAddUser">
            {{ $t("common.confirm") }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="addGroupOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ $t("webchat.addGroup") }}</DialogTitle>
          <DialogDescription>{{
            $t("webchat.addGroupDesc")
          }}</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <Label for="wc-gid">{{ $t("webchat.groupId") }}</Label>
            <Input
              id="wc-gid"
              v-model="newGroupId"
              :placeholder="$t('webchat.sceneIdPlaceholder')"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="wc-gname">{{ $t("webchat.groupName") }}</Label>
            <Input
              id="wc-gname"
              v-model="newGroupName"
              :placeholder="$t('webchat.optional')"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="addGroupOpen = false">
            {{ $t("common.cancel") }}
          </Button>
          <Button :disabled="!newGroupId.trim()" @click="onAddGroup">
            {{ $t("common.confirm") }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <ImageLightbox
      :images="imageList.map(e => ({ url: e.url }))"
      :initial-index="lightboxIndex"
      :open="lightboxOpen"
      @update:open="lightboxOpen = $event"
    />
  </div>
</template>
