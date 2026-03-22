<template>
  <div class="d-flex flex-column ga-4" style="height: calc(100vh - 100px)">
    <div class="d-flex align-center">
      <h1 class="text-h4">{{ t('chat.title') }}</h1>
      <v-spacer />
      <v-chip :color="connected ? 'success' : 'error'" variant="tonal">
        {{ connected ? t('chat.connected') : t('chat.disconnected') }}
      </v-chip>
    </div>

    <v-row class="flex-grow-1" style="min-height: 0">
      <v-col cols="12" md="4" lg="3">
        <v-card>
          <v-card-title>{{ t('chat.sessionConfig') }}</v-card-title>
          <v-card-text class="d-flex flex-column ga-4">
            <v-text-field
              v-model="sessionForm.target_user_id"
              :label="t('chat.userId')"
              variant="outlined"
              density="comfortable"
              @keydown.enter.prevent="saveSession"
            />

            <div class="session-entry-actions">
              <v-btn
                color="primary"
                class="session-entry-actions__primary"
                :disabled="!connected"
                @click="saveSession"
              >
                {{ t('chat.enterSession') }}
              </v-btn>
              <v-btn
                variant="tonal"
                class="session-entry-actions__secondary"
                :disabled="!connected"
                @click="reconnect"
              >
                {{ t('chat.reconnect') }}
              </v-btn>
            </div>

            <v-alert
              v-if="session"
              type="info"
              variant="tonal"
              density="comfortable"
              :title="t('chat.currentSession')"
            >
              <div>{{ t('chat.currentUser', { userId: session.target_user_id }) }}</div>
              <div class="mt-2 d-flex ga-2">
                <v-btn
                  size="small"
                  variant="text"
                  color="warning"
                  @click="clearCurrentSessionHistory"
                >
                  {{ t('chat.clearHistory') }}
                </v-btn>
                <v-btn
                  size="small"
                  variant="text"
                  color="error"
                  @click="deleteSessionItem({ session, message_count: messages.length })"
                >
                  {{ t('chat.deleteSession') }}
                </v-btn>
              </div>
            </v-alert>

            <v-alert
              v-if="capabilities"
              type="success"
              variant="tonal"
              density="comfortable"
              :title="t('chat.capabilities')"
            >
              {{ t('chat.supportedSegments', { segments: capabilities.segment_types.join(', ') }) }}
            </v-alert>

            <v-card v-if="recentSessions.length" variant="outlined">
              <v-card-title class="text-subtitle-1">{{ t('chat.recentSessions') }}</v-card-title>
              <v-list density="compact" lines="two">
                <v-list-item
                  v-for="recent in recentSessions"
                  :key="recent.session.session_id"
                  :active="session?.session_id === recent.session.session_id"
                  rounded="lg"
                  @click="switchToSession(recent)"
                >
                  <template #append>
                    <div class="d-flex align-center ga-1">
                      <v-chip
                        size="x-small"
                        variant="tonal"
                        :color="sessionStatusColor(recent.session.status)"
                      >
                        {{ recent.session.status }}
                      </v-chip>
                      <v-btn
                        icon="mdi-delete-outline"
                        size="x-small"
                        variant="text"
                        color="error"
                        @click.stop="deleteSessionItem(recent)"
                      />
                    </div>
                  </template>
                  <v-list-item-title class="d-flex align-center ga-2">
                    <span>{{ recent.session.target_user_id }}</span>
                    <span class="text-caption text-medium-emphasis">
                      {{ t('chat.messageCount', { count: recent.message_count }) }}
                    </span>
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    {{
                      formatSessionTime(
                        recent.last_message_at || recent.session.updated_at || recent.session.created_at,
                      ) || t('chat.justNow')
                    }}
                  </v-list-item-subtitle>
                  <v-list-item-subtitle class="session-preview">
                    {{ summarizeSessionItem(recent) }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8" lg="9" style="min-height: 0">
        <v-card class="fill-height d-flex flex-column" style="min-height: 0">
          <div ref="messagesContainer" class="flex-grow-1 pa-4" style="overflow-y: auto">
            <div v-for="message in messages" :key="message.message_id + message.timestamp" class="mb-3">
              <div v-if="message.role === 'system'" class="text-center">
                <v-chip size="small" color="grey" variant="tonal">
                  {{ getTextContent(message.segments) }}
                </v-chip>
              </div>

              <div v-else-if="message.role === 'error'" class="d-flex justify-start">
                <v-card color="error" variant="tonal" class="pa-3" max-width="80%" rounded="lg">
                  <template v-for="(segment, index) in message.segments" :key="index">
                    <div v-if="segment.type === 'text'">{{ segment.text }}</div>
                  </template>
                </v-card>
              </div>

              <div v-else :class="message.role === 'user' ? 'd-flex justify-end' : 'd-flex justify-start'">
                <v-card
                  :color="message.role === 'user' ? 'primary' : undefined"
                  :variant="message.role === 'user' ? 'tonal' : 'outlined'"
                  class="pa-3"
                  :class="{ 'image-message-card': hasImageSegment(message.segments) }"
                  :style="getMessageCardStyle(message.segments)"
                  rounded="lg"
                >
                  <div class="d-flex flex-column ga-2">
                    <template v-for="(segment, index) in message.segments" :key="index">
                      <div v-if="segment.type === 'reply'" class="reply-segment">
                        <div class="reply-segment__label">{{ t('chat.replyMessage') }}</div>
                        <div class="reply-segment__id">#{{ segment.message_id }}</div>
                        <div v-if="segment.text" class="reply-segment__text">{{ segment.text }}</div>
                      </div>
                      <div v-else-if="segment.type === 'text'" class="text-body-2" style="white-space: pre-wrap">
                        {{ segment.text }}
                      </div>
                      <v-chip
                        v-else-if="segment.type === 'mention'"
                        size="small"
                        variant="tonal"
                        color="secondary"
                        class="align-self-start"
                      >
                        @{{ segment.display || segment.target }}
                      </v-chip>
                      <img
                        v-else-if="segment.type === 'image' && resolveImageUrl(segment)"
                        :src="resolveImageUrl(segment)"
                        :alt="segment.alt || t('chat.imageAlt')"
                        class="chat-image"
                        @click="openImagePreview(segment)"
                      />
                      <pre
                        v-else-if="segment.type === 'raw'"
                        class="text-body-2"
                        style="white-space: pre-wrap; margin: 0"
                      >{{ JSON.stringify(segment.data, null, 2) }}</pre>
                    </template>
                  </div>
                  <div class="d-flex justify-end mt-2">
                    <v-btn
                      size="x-small"
                      variant="text"
                      prepend-icon="mdi-reply-outline"
                      @click="startReplyToMessage(message)"
                    >
                      {{ t('chat.replyButton') }}
                    </v-btn>
                  </div>
                </v-card>
              </div>
            </div>
          </div>

          <v-divider />

          <div class="pa-4 d-flex flex-column ga-3">
            <div v-if="pendingReply" class="pending-reply">
              <div class="pending-reply__content">
                <div class="pending-reply__label">
                  {{ t('chat.replyingTo', { role: replyRoleLabel(pendingReply.role) }) }}
                </div>
                <div class="pending-reply__id">#{{ pendingReply.message_id }}</div>
                <div class="pending-reply__text">{{ summarizeReplyMessage(pendingReply) }}</div>
              </div>
              <v-btn
                icon="mdi-close"
                size="small"
                variant="text"
                @click="clearPendingReply"
              />
            </div>

            <div v-if="orderedComposerImages.length" class="composer-attachments">
              <div
                v-for="(image, index) in orderedComposerImages"
                :key="image.id"
                class="composer-attachment-item"
                :class="{ 'composer-attachment-item--selected': selectedComposerImageId === image.id }"
                @click="selectComposerImage(image.id)"
              >
                <div class="composer-attachment-index">{{ t('chat.imageIndex', { index: index + 1 }) }}</div>
                <img
                  :src="image.previewUrl"
                  :alt="image.name"
                  class="composer-attachment-thumb"
                  @click="openImagePreviewFromPending(image)"
                />
                <div class="composer-attachment-meta">
                  <div class="composer-attachment-name">{{ image.name }}</div>
                  <div class="composer-attachment-size">{{ formatBytes(image.size) || t('chat.imageFallback') }}</div>
                </div>
                <v-btn
                  icon="mdi-cursor-move"
                  size="x-small"
                  variant="text"
                  @click="moveComposerImageToCursor(image.id)"
                />
                <v-btn
                  icon="mdi-close"
                  size="x-small"
                  variant="text"
                  @click="removeComposerImage(image.id)"
                />
              </div>
            </div>

            <div
              ref="composerRef"
              class="composer"
              :class="{ 'composer--disabled': !connected || !session }"
              contenteditable="true"
              spellcheck="false"
              :data-placeholder="t('chat.composerPlaceholder')"
              @input="handleComposerInput"
              @keydown="handleComposerKeydown"
              @mouseup="captureComposerSelection"
              @keyup="captureComposerSelection"
              @focus="captureComposerSelection"
              @click="handleComposerClick"
              @paste="handleComposerPaste"
            />

            <input
              ref="imageInputRef"
              type="file"
              accept="image/*"
              multiple
              class="d-none"
              @change="handleImageSelection"
            />

            <div class="d-flex align-center">
              <div class="text-caption text-grey">
                {{ principal ? t('chat.currentPrincipal', { username: principal.username }) : t('chat.unauthenticated') }}
              </div>
              <v-spacer />
              <v-btn
                variant="text"
                :disabled="!connected || !session"
                @click="insertMentionForCurrentSession"
              >
                {{ t('chat.mentionCurrentUser') }}
              </v-btn>
              <v-btn
                variant="tonal"
                :disabled="!connected || !session || isPreparingImages"
                @click="pickImages"
              >
                {{ t('chat.pickImage') }}
              </v-btn>
              <v-btn
                color="primary"
                :loading="isPreparingImages"
                :disabled="!connected || !session || !composerHasContent"
                @click="send"
              >
                {{ t('common.send') }}
              </v-btn>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="imagePreviewVisible" max-width="1200">
      <v-card class="pa-2 preview-card">
        <div class="d-flex justify-space-between align-center px-2">
          <div class="text-caption text-grey-lighten-1">
            {{ t('chat.zoom', { value: Math.round(previewScale * 100) }) }}
          </div>
          <div class="d-flex align-center ga-1">
            <v-btn icon="mdi-magnify-minus-outline" variant="text" @click="zoomOutPreview" />
            <v-btn icon="mdi-fit-to-screen-outline" variant="text" @click="resetPreviewTransform" />
            <v-btn icon="mdi-magnify-plus-outline" variant="text" @click="zoomInPreview" />
            <v-btn icon="mdi-download-outline" variant="text" @click="downloadPreviewImage" />
          </div>
          <div class="d-flex justify-end">
          <v-btn icon="mdi-close" variant="text" @click="closeImagePreview" />
          </div>
        </div>
        <div class="px-4 pb-2 text-caption text-grey-lighten-1 preview-meta">
          <span v-if="previewImageNaturalWidth && previewImageNaturalHeight">
            {{ previewImageNaturalWidth }} × {{ previewImageNaturalHeight }}
          </span>
          <span v-if="previewImageSizeText">
            {{ previewImageSizeText }}
          </span>
        </div>
        <div ref="previewWrapRef" class="preview-image-wrap">
          <img
            v-if="imagePreviewSrc"
            ref="previewImageRef"
            :src="imagePreviewSrc"
            :alt="imagePreviewAlt"
            draggable="false"
            class="preview-image"
            :style="previewImageStyle"
            @mousedown="startImageDrag"
            @dragstart.prevent
            @load="handlePreviewImageLoad"
            @dblclick="togglePreviewZoom"
            @wheel.prevent="handlePreviewWheel"
          />
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChatClient } from '@/api/chat'
import type {
  CapabilitiesResponsePayload,
  ChatCapabilities,
  ChatEnvelope,
  ChatSegment,
  ChatSessionState,
  ImageSegment,
  MessageReceivePayload,
  MessageRole,
  SessionDeletedPayload,
  SessionListItem,
  SessionListPayload,
  SessionCreatePayload,
  SessionStatePayload,
  WebUIPrincipal,
} from '@/types/chat'

const client = new ChatClient()
let composerRange: Range | null = null
const { t } = useI18n()

interface PendingImage {
  id: string
  name: string
  size: number
  mime: string
  base64: string
  previewUrl: string
}

interface PendingMention {
  id: string
  target: string
  display: string
}

const connected = ref(false)
const principal = ref<WebUIPrincipal | null>(null)
const capabilities = ref<ChatCapabilities | null>(null)
const session = ref<ChatSessionState | null>(null)
const recentSessions = ref<SessionListItem[]>([])
const messages = ref<MessageReceivePayload[]>([])
const pendingReply = ref<MessageReceivePayload | null>(null)
const messagesContainer = ref<HTMLElement>()
const composerRef = ref<HTMLDivElement>()
const imageInputRef = ref<HTMLInputElement>()
const isPreparingImages = ref(false)
const composerVersion = ref(0)
const selectedComposerImageId = ref<string | null>(null)
const imagePreviewVisible = ref(false)
const imagePreviewSrc = ref('')
const imagePreviewAlt = ref(t('chat.imageAlt'))
const previewScale = ref(1)
const previewOffsetX = ref(0)
const previewOffsetY = ref(0)
const previewImageRef = ref<HTMLImageElement>()
const previewWrapRef = ref<HTMLElement>()
const previewBaseScale = ref(1)
const previewImageNaturalWidth = ref(0)
const previewImageNaturalHeight = ref(0)
const previewImageSizeText = ref('')
const isDraggingPreview = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragOriginX = ref(0)
const dragOriginY = ref(0)
const composerImages = new Map<string, PendingImage>()
const composerMentions = new Map<string, PendingMention>()

const sessionForm = reactive<SessionCreatePayload>({
  target_user_id: '10001',
})

function appendMessage(message: MessageReceivePayload) {
  messages.value.push(message)
  scrollToBottom()
}

function appendSimpleMessage(role: 'system' | 'error', text: string) {
  appendMessage({
    session_id: session.value?.session_id ?? 'system',
    message_id: `${role}_${Date.now()}`,
    role,
    segments: [{ type: 'text', text }],
    timestamp: new Date().toISOString(),
  })
}

function summarizeReplyMessage(message: MessageReceivePayload) {
  const text = getTextContent(message.segments).trim()
  return text || t('chat.imageSummary')
}

function replyRoleLabel(role: MessageRole) {
  if (role === 'user') return t('chat.yourMessage')
  if (role === 'bot') return t('chat.botMessage')
  if (role === 'system') return t('chat.systemMessage')
  return t('chat.errorMessage')
}

function startReplyToMessage(message: MessageReceivePayload) {
  pendingReply.value = message
  focusComposer(true)
}

function clearPendingReply() {
  pendingReply.value = null
}

function clearCurrentSessionHistory() {
  if (!session.value) return
  client.clearHistory()
  clearPendingReply()
}

function resetActiveSessionState() {
  session.value = null
  messages.value = []
  clearPendingReply()
  clearComposer()
}

function switchToSession(target: SessionListItem) {
  if (session.value?.session_id === target.session.session_id) return
  sessionForm.target_user_id = target.session.target_user_id
  client.updateSession({
    session_id: target.session.session_id,
    target_user_id: target.session.target_user_id,
  })
}

function deleteSessionItem(target: SessionListItem) {
  const confirmed = window.confirm(
    t('chat.confirmDelete', { userId: target.session.target_user_id }),
  )
  if (!confirmed) return
  client.deleteSession({ session_id: target.session.session_id })
}

function formatSessionTime(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString()
}

function sessionStatusColor(status: ChatSessionState['status']) {
  if (status === 'ready') return 'success'
  if (status === 'closed') return 'grey'
  return 'error'
}

function summarizeSessionItem(item: SessionListItem) {
  const summary = item.last_message?.trim()
  if (summary) return summary
  if (item.message_count > 0) return t('chat.existingMessages')
  return t('chat.noMessages')
}

const composerHasContent = computed(() => {
  const segments = buildComposerSegments()
  return segments.length > 0 && segments.some((segment) => {
    if (segment.type === 'text') {
      return segment.text.trim().length > 0
    }
    return true
  })
})

const orderedComposerImages = computed(() => {
  composerVersion.value
  const composer = composerRef.value
  if (!composer) return [] as PendingImage[]

  const ids = Array.from(
    composer.querySelectorAll<HTMLElement>('[data-kind="image-token"][data-image-id]'),
  )
    .map((node) => node.dataset.imageId || '')
    .filter(Boolean)

  return ids
    .map((id) => composerImages.get(id))
    .filter((image): image is PendingImage => Boolean(image))
})

function pickImages() {
  imageInputRef.value?.click()
}

function insertMentionForCurrentSession() {
  if (!session.value) return
  const mention: PendingMention = {
    id: `mention_${session.value.target_user_id}_${Date.now()}`,
    target: session.value.target_user_id,
    display: session.value.target_user_id,
  }
  composerMentions.set(mention.id, mention)
  insertMentionIntoComposer(mention)
}

async function handleImageSelection(event: Event) {
  const target = event.target as HTMLInputElement | null
  const files = Array.from(target?.files || [])
  if (!files.length) return

  isPreparingImages.value = true
  try {
    const images = await Promise.all(files.map(readImageFile))
    for (const image of images) {
      composerImages.set(image.id, image)
      insertImageIntoComposer(image)
    }
  } finally {
    isPreparingImages.value = false
    if (target) {
      target.value = ''
    }
  }
}

function getTextContent(segments: ChatSegment[]) {
  return segments
    .map((segment) => {
      if (segment.type === 'text') return segment.text
      if (segment.type === 'image') return t('chat.imageToken')
      if (segment.type === 'mention') return `@${segment.display || segment.target}`
      if (segment.type === 'reply') return t('chat.replySummary', { messageId: segment.message_id })
      return `[${segment.segment_type}]`
    })
    .join(' ')
}

function hasImageSegment(segments: ChatSegment[]) {
  return segments.some((segment) => segment.type === 'image')
}

function hasMentionSegment(segments: ChatSegment[]) {
  return segments.some((segment) => segment.type === 'mention')
}

function hasReplySegment(segments: ChatSegment[]) {
  return segments.some((segment) => segment.type === 'reply')
}

function getMessageCardStyle(segments: ChatSegment[]) {
  if (hasImageSegment(segments)) {
    return {
      width: 'fit-content',
      maxWidth: 'min(720px, 78vw)',
    }
  }

  if (hasReplySegment(segments) || hasMentionSegment(segments)) {
    return {
      maxWidth: 'min(80%, 720px)',
    }
  }

  return {
    maxWidth: '80%',
  }
}

function resolveImageUrl(segment: ImageSegment) {
  if (segment.base64) {
    return `data:${segment.mime || 'image/png'};base64,${segment.base64}`
  }
  const rawUrl = segment.url
  if (!rawUrl) return ''
  if (!rawUrl.startsWith('/api/chat/assets/')) return rawUrl
  const token = localStorage.getItem('token')
  if (!token) return rawUrl
  const separator = rawUrl.includes('?') ? '&' : '?'
  return `${rawUrl}${separator}token=${encodeURIComponent(token)}`
}

function openImagePreview(segment: ImageSegment) {
  const src = resolveImageUrl(segment)
  if (!src) return
  imagePreviewSrc.value = src
  imagePreviewAlt.value = segment.alt || t('chat.imageAlt')
  previewImageNaturalWidth.value = 0
  previewImageNaturalHeight.value = 0
  previewImageSizeText.value = estimateImageSize(segment)
  resetPreviewTransform()
  imagePreviewVisible.value = true
}

function closeImagePreview() {
  imagePreviewVisible.value = false
  imagePreviewSrc.value = ''
  stopImageDrag()
  resetPreviewTransform()
}

function resetPreviewTransform() {
  previewScale.value = previewBaseScale.value
  previewOffsetX.value = 0
  previewOffsetY.value = 0
}

function zoomInPreview() {
  setPreviewScale(previewScale.value + 0.2)
}

function zoomOutPreview() {
  setPreviewScale(previewScale.value - 0.2)
}

function handlePreviewWheel(event: WheelEvent) {
  setPreviewScale(previewScale.value + (event.deltaY < 0 ? 0.12 : -0.12))
}

const previewBounds = computed(() => {
  const img = previewImageRef.value
  const wrap = previewWrapRef.value
  if (!img || !wrap) {
    return { maxX: 0, maxY: 0 }
  }

  const scaledWidth = img.clientWidth * previewScale.value
  const scaledHeight = img.clientHeight * previewScale.value
  const maxX = Math.max(0, (scaledWidth - wrap.clientWidth) / 2)
  const maxY = Math.max(0, (scaledHeight - wrap.clientHeight) / 2)
  return { maxX, maxY }
})

const canDragPreview = computed(() => previewBounds.value.maxX > 0 || previewBounds.value.maxY > 0)

const previewImageStyle = computed(() => ({
  transform: `translate(${previewOffsetX.value}px, ${previewOffsetY.value}px) scale(${previewScale.value})`,
  transformOrigin: 'center center',
  cursor: isDraggingPreview.value ? 'grabbing' : canDragPreview.value ? 'grab' : 'zoom-in',
}))

function startImageDrag(event: MouseEvent) {
  if (event.button !== 0) return
  if (!canDragPreview.value) return
  event.preventDefault()
  isDraggingPreview.value = true
  dragStartX.value = event.clientX
  dragStartY.value = event.clientY
  dragOriginX.value = previewOffsetX.value
  dragOriginY.value = previewOffsetY.value
  window.addEventListener('mousemove', onImageDrag)
  window.addEventListener('mouseup', stopImageDrag)
  window.addEventListener('mouseleave', stopImageDrag)
  window.addEventListener('blur', stopImageDrag)
}

function onImageDrag(event: MouseEvent) {
  if (!isDraggingPreview.value) return
  event.preventDefault()
  previewOffsetX.value = dragOriginX.value + event.clientX - dragStartX.value
  previewOffsetY.value = dragOriginY.value + event.clientY - dragStartY.value
  clampPreviewOffset()
}

function stopImageDrag() {
  if (!isDraggingPreview.value) {
    window.removeEventListener('mousemove', onImageDrag)
    window.removeEventListener('mouseup', stopImageDrag)
    window.removeEventListener('mouseleave', stopImageDrag)
    window.removeEventListener('blur', stopImageDrag)
    return
  }
  isDraggingPreview.value = false
  window.removeEventListener('mousemove', onImageDrag)
  window.removeEventListener('mouseup', stopImageDrag)
  window.removeEventListener('mouseleave', stopImageDrag)
  window.removeEventListener('blur', stopImageDrag)
}

function setPreviewScale(next: number) {
  previewScale.value = Math.min(5, Math.max(0.5, Number(next.toFixed(2))))
  clampPreviewOffset()
}

function clampPreviewOffset() {
  const { maxX, maxY } = previewBounds.value
  previewOffsetX.value = Math.min(maxX, Math.max(-maxX, previewOffsetX.value))
  previewOffsetY.value = Math.min(maxY, Math.max(-maxY, previewOffsetY.value))
}

function downloadPreviewImage() {
  if (!imagePreviewSrc.value) return
  const link = document.createElement('a')
  link.href = imagePreviewSrc.value
  link.download = 'chat-image.png'
  link.click()
}

function handlePreviewImageLoad() {
  const img = previewImageRef.value
  const wrap = previewWrapRef.value
  if (!img || !wrap) return

  previewImageNaturalWidth.value = img.naturalWidth
  previewImageNaturalHeight.value = img.naturalHeight

  const fitScale = Math.min(
    1,
    wrap.clientWidth / img.naturalWidth,
    wrap.clientHeight / img.naturalHeight,
  )
  previewBaseScale.value = Number(Math.max(0.5, fitScale).toFixed(2))
  resetPreviewTransform()
}

function togglePreviewZoom() {
  const fit = previewBaseScale.value
  const current = previewScale.value
  if (Math.abs(current - fit) < 0.05) {
    setPreviewScale(1)
    return
  }
  if (Math.abs(current - 1) < 0.05) {
    setPreviewScale(2)
    return
  }
  resetPreviewTransform()
}

function estimateImageSize(segment: ImageSegment) {
  if (segment.base64) {
    const padding = segment.base64.endsWith('==') ? 2 : segment.base64.endsWith('=') ? 1 : 0
    const bytes = Math.max(0, Math.floor(segment.base64.length * 3 / 4) - padding)
    return formatBytes(bytes)
  }
  return ''
}

function formatBytes(bytes: number) {
  if (bytes <= 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function readImageFile(file: File): Promise<PendingImage> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error || new Error(t('chat.imageReadFailed')))
    reader.readAsDataURL(file)
  })

  const [prefix, base64 = ''] = dataUrl.split(',', 2)
  const mimeMatch = prefix.match(/^data:(.+);base64$/)

  return {
    id: `${file.name}_${file.lastModified}_${Math.random().toString(16).slice(2)}`,
    name: file.name,
    size: file.size,
    mime: mimeMatch?.[1] || file.type || 'image/png',
    base64,
    previewUrl: dataUrl,
  }
}

function touchComposer() {
  composerVersion.value += 1
}

function captureComposerSelection() {
  const composer = composerRef.value
  if (!composer) return
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return
  const range = selection.getRangeAt(0)
  if (!composer.contains(range.commonAncestorContainer)) return
  composerRange = range.cloneRange()
}

function focusComposer(placeAtEnd = false) {
  const composer = composerRef.value
  if (!composer) return
  composer.focus()
  const selection = window.getSelection()
  if (!selection) return

  let range = composerRange
  if (placeAtEnd || !range || !composer.contains(range.commonAncestorContainer)) {
    range = document.createRange()
    range.selectNodeContents(composer)
    range.collapse(false)
  }

  selection.removeAllRanges()
  selection.addRange(range)
  composerRange = range.cloneRange()
}

function insertTextAtCursor(text: string) {
  focusComposer()
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return
  const range = selection.getRangeAt(0)
  range.deleteContents()
  const node = document.createTextNode(text)
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  composerRange = range.cloneRange()
  touchComposer()
}

function createComposerImageNode(image: PendingImage) {
  const wrapper = document.createElement('span')
  wrapper.className = 'composer-image-token'
  wrapper.contentEditable = 'false'
  wrapper.dataset.imageId = image.id
  wrapper.dataset.kind = 'image-token'

  const label = document.createElement('span')
  label.className = 'composer-image-token__label'
  label.dataset.role = 'token-label'
  label.textContent = t('chat.imageToken')

  const remove = document.createElement('button')
  remove.type = 'button'
  remove.className = 'composer-image-token__remove'
  remove.dataset.action = 'remove-image'
  remove.dataset.imageId = image.id
  remove.textContent = '×'

  wrapper.append(label, remove)
  return wrapper
}

function createComposerMentionNode(mention: PendingMention) {
  const wrapper = document.createElement('span')
  wrapper.className = 'composer-mention-token'
  wrapper.contentEditable = 'false'
  wrapper.dataset.mentionId = mention.id
  wrapper.dataset.kind = 'mention-token'

  const label = document.createElement('span')
  label.className = 'composer-mention-token__label'
  label.textContent = `@${mention.display}`

  const remove = document.createElement('button')
  remove.type = 'button'
  remove.className = 'composer-mention-token__remove'
  remove.dataset.action = 'remove-mention'
  remove.dataset.mentionId = mention.id
  remove.textContent = '×'

  wrapper.append(label, remove)
  return wrapper
}

function getComposerImageToken(id: string) {
  return composerRef.value?.querySelector<HTMLElement>(`[data-kind="image-token"][data-image-id="${id}"]`) || null
}

function syncComposerImageTokenState() {
  const composer = composerRef.value
  if (!composer) return
  const tokens = Array.from(
    composer.querySelectorAll<HTMLElement>('[data-kind="image-token"][data-image-id]'),
  )
  tokens.forEach((token) => {
    const active = token.dataset.imageId === selectedComposerImageId.value
    token.classList.toggle('composer-image-token--selected', active)
  })
}

function selectComposerImage(id: string | null) {
  selectedComposerImageId.value = id
  syncComposerImageTokenState()
}

function insertImageIntoComposer(image: PendingImage) {
  focusComposer()
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return
  const range = selection.getRangeAt(0)
  range.deleteContents()

  const token = createComposerImageNode(image)
  const caretAnchor = document.createTextNode('')
  range.insertNode(caretAnchor)
  range.insertNode(token)

  range.setStart(caretAnchor, 0)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  composerRange = range.cloneRange()
  syncComposerImageTokenLabels()
  selectComposerImage(image.id)
  touchComposer()
}

function insertMentionIntoComposer(mention: PendingMention) {
  focusComposer()
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return
  const range = selection.getRangeAt(0)
  range.deleteContents()

  const token = createComposerMentionNode(mention)
  const caretAnchor = document.createTextNode('')
  range.insertNode(caretAnchor)
  range.insertNode(token)

  range.setStart(caretAnchor, 0)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  composerRange = range.cloneRange()
  touchComposer()
}

function removeComposerImage(id: string) {
  const composer = composerRef.value
  if (!composer) return
  const node = composer.querySelector<HTMLElement>(`[data-image-id="${id}"]`)
  node?.remove()
  composerImages.delete(id)
  if (selectedComposerImageId.value === id) {
    selectComposerImage(null)
  }
  focusComposer(true)
  syncComposerImageTokenLabels()
  touchComposer()
}

function removeComposerMention(id: string) {
  const composer = composerRef.value
  if (!composer) return
  const node = composer.querySelector<HTMLElement>(`[data-kind="mention-token"][data-mention-id="${id}"]`)
  node?.remove()
  composerMentions.delete(id)
  focusComposer(true)
  touchComposer()
}

function placeCaretAroundToken(node: HTMLElement, direction: 'before' | 'after') {
  const selection = window.getSelection()
  if (!selection) return
  const range = document.createRange()
  if (direction === 'before') {
    range.setStartBefore(node)
  } else {
    range.setStartAfter(node)
  }
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  composerRange = range.cloneRange()
}

function moveComposerImageToCursor(id: string) {
  const token = getComposerImageToken(id)
  if (!token) return
  focusComposer()
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return
  const range = selection.getRangeAt(0)
  if (token.contains(range.commonAncestorContainer)) {
    return
  }
  token.remove()
  range.deleteContents()
  const caretAnchor = document.createTextNode('')
  range.insertNode(caretAnchor)
  range.insertNode(token)
  range.setStart(caretAnchor, 0)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  composerRange = range.cloneRange()
  syncComposerImageTokenLabels()
  selectComposerImage(id)
  touchComposer()
}

function handleComposerInput() {
  syncComposerImageTokenLabels()
  syncComposerImageTokenState()
  touchComposer()
  captureComposerSelection()
}

function handleComposerKeydown(event: KeyboardEvent) {
  const selectedId = selectedComposerImageId.value
  if (selectedId) {
    const token = getComposerImageToken(selectedId)
    if (token) {
      if (event.key === 'Backspace' || event.key === 'Delete') {
        event.preventDefault()
        removeComposerImage(selectedId)
        return
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        selectComposerImage(null)
        placeCaretAroundToken(token, 'before')
        return
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        selectComposerImage(null)
        placeCaretAroundToken(token, 'after')
        return
      }
    }
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

function handleComposerClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target) return
  const removeButton = target.closest<HTMLElement>('[data-action="remove-image"]')
  if (removeButton?.dataset.imageId) {
    event.preventDefault()
    removeComposerImage(removeButton.dataset.imageId)
    return
  }
  const removeMentionButton = target.closest<HTMLElement>('[data-action="remove-mention"]')
  if (removeMentionButton?.dataset.mentionId) {
    event.preventDefault()
    removeComposerMention(removeMentionButton.dataset.mentionId)
    return
  }
  const token = target.closest<HTMLElement>('[data-kind="image-token"][data-image-id]')
  if (token?.dataset.imageId) {
    event.preventDefault()
    selectComposerImage(token.dataset.imageId)
    return
  }
  selectComposerImage(null)
  captureComposerSelection()
}

function handleComposerPaste(event: ClipboardEvent) {
  event.preventDefault()
  const text = event.clipboardData?.getData('text/plain') || ''
  if (text) {
    insertTextAtCursor(text)
  }
}

function syncComposerImageTokenLabels() {
  const composer = composerRef.value
  if (!composer) return
  const tokens = Array.from(
    composer.querySelectorAll<HTMLElement>('[data-kind="image-token"][data-image-id]'),
  )
  tokens.forEach((token, index) => {
    const label = token.querySelector<HTMLElement>('[data-role="token-label"]')
    if (label) {
      label.textContent = t('chat.imageIndexedToken', { index: index + 1 })
    }
  })
}

function buildComposerSegments(): ChatSegment[] {
  composerVersion.value
  const composer = composerRef.value
  if (!composer) return []

  const segments: ChatSegment[] = []
  let textBuffer = ''

  const flushText = () => {
    if (textBuffer) {
      segments.push({ type: 'text', text: textBuffer })
      textBuffer = ''
    }
  }

  const walkNode = (node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      textBuffer += node.textContent || ''
      return
    }

    if (!(node instanceof HTMLElement)) {
      return
    }

    if (node.dataset.kind === 'image-token' && node.dataset.imageId) {
      const image = composerImages.get(node.dataset.imageId)
      if (image) {
        flushText()
        segments.push({
          type: 'image',
          base64: image.base64,
          mime: image.mime,
          alt: image.name,
        })
      }
      return
    }

    if (node.dataset.kind === 'mention-token' && node.dataset.mentionId) {
      const mention = composerMentions.get(node.dataset.mentionId)
      if (mention) {
        flushText()
        segments.push({
          type: 'mention',
          target: mention.target,
          display: mention.display,
          mention_type: 'user',
        })
      }
      return
    }

    if (node.tagName === 'BR') {
      textBuffer += '\n'
      return
    }

    const isBlock = ['DIV', 'P'].includes(node.tagName)
    if (isBlock && textBuffer && !textBuffer.endsWith('\n')) {
      textBuffer += '\n'
    }
    node.childNodes.forEach(walkNode)
    if (isBlock && textBuffer && !textBuffer.endsWith('\n')) {
      textBuffer += '\n'
    }
  }

  composer.childNodes.forEach(walkNode)
  flushText()

  return segments
    .map((segment) => {
      if (segment.type !== 'text') return segment
      return { ...segment, text: segment.text.replace(/\u00A0/g, ' ') }
    })
    .filter((segment) => segment.type !== 'text' || segment.text.length > 0)
}

function clearComposer() {
  const composer = composerRef.value
  if (composer) {
    composer.innerHTML = ''
  }
  composerImages.forEach((image) => {
    URL.revokeObjectURL(image.previewUrl)
  })
  composerImages.clear()
  composerMentions.clear()
  composerRange = null
  selectComposerImage(null)
  touchComposer()
}

function openImagePreviewFromPending(image: PendingImage) {
  imagePreviewSrc.value = image.previewUrl
  imagePreviewAlt.value = image.name
  previewImageNaturalWidth.value = 0
  previewImageNaturalHeight.value = 0
  previewImageSizeText.value = formatBytes(image.size)
  resetPreviewTransform()
  imagePreviewVisible.value = true
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && imagePreviewVisible.value) {
    closeImagePreview()
  }
}

function handleEnvelope(event: ChatEnvelope) {
  switch (event.type) {
    case 'auth.ok':
      principal.value = (event.payload as { principal: WebUIPrincipal }).principal
      client.requestCapabilities()
      appendSimpleMessage('system', t('chat.authOk'))
      break
    case 'capabilities.response':
      capabilities.value = (event.payload as CapabilitiesResponsePayload).capabilities
      break
    case 'session.list':
      recentSessions.value = (event.payload as SessionListPayload).sessions
      break
    case 'session.deleted': {
      const payload = event.payload as SessionDeletedPayload
      recentSessions.value = recentSessions.value.filter(
        (item) => item.session.session_id !== payload.session_id,
      )
      if (session.value?.session_id === payload.session_id) {
        resetActiveSessionState()
        appendSimpleMessage('system', t('chat.sessionDeleted'))
      }
      break
    }
    case 'session.state': {
      const payload = event.payload as SessionStatePayload
      const hadSession = Boolean(session.value)
      session.value = payload.session
      sessionForm.target_user_id = payload.session.target_user_id
      messages.value = payload.history
      if (!hadSession && payload.history.length === 0) {
        appendSimpleMessage('system', t('chat.sessionReady'))
      }
      break
    }
    case 'session.history_cleared': {
      const payload = event.payload as SessionStatePayload
      session.value = payload.session
      messages.value = payload.history
      clearPendingReply()
      break
    }
    case 'message.receive':
      appendMessage(event.payload as MessageReceivePayload)
      break
    case 'message.error':
    case 'auth.error':
    case 'system.error': {
      const payload = event.payload as { message?: string; code?: string }
      appendSimpleMessage('error', payload.message || payload.code || t('common.unknownError'))
      break
    }
    case 'system.info':
    case 'system.warning': {
      const payload = event.payload as { message?: string }
      appendSimpleMessage('system', payload.message || t('chat.systemFallback'))
      break
    }
  }
}

function connect() {
  client.connect()
}

function reconnect() {
  client.disconnect()
  resetActiveSessionState()
  connect()
}

function saveSession() {
  if (!connected.value) return
  const payload: SessionCreatePayload = {
    target_user_id: sessionForm.target_user_id,
  }
  client.createSession(payload)
}

function send() {
  if (!session.value) return
  const segments = buildComposerSegments()
  if (pendingReply.value) {
    segments.unshift({
      type: 'reply',
      message_id: pendingReply.value.message_id,
      text: summarizeReplyMessage(pendingReply.value),
    })
  }
  if (!segments.length) return
  client.sendMessage({
    session_id: session.value.session_id,
    message_id: `cli_${Date.now()}`,
    segments,
  })
  clearComposer()
  clearPendingReply()
}

function scrollToBottom() {
  nextTick(() => {
    messagesContainer.value?.scrollTo(0, messagesContainer.value.scrollHeight)
  })
}

const unsubscribeMessage = client.onMessage(handleEnvelope)
const unsubscribeOpen = client.onOpen(() => {
  connected.value = true
  const token = localStorage.getItem('token')
  if (!token) {
    appendSimpleMessage('error', t('chat.tokenMissing'))
    return
  }
  client.authenticate(token)
  client.listSessions()
})
const unsubscribeClose = client.onClose(() => {
  connected.value = false
  appendSimpleMessage('system', t('chat.connectionClosed'))
})

onMounted(() => {
  connect()
  window.addEventListener('keydown', handleWindowKeydown)
})
onUnmounted(() => {
  if (connected.value && session.value) {
    client.closeSession()
  }
  stopImageDrag()
  unsubscribeMessage()
  unsubscribeOpen()
  unsubscribeClose()
  client.disconnect()
  clearComposer()
  window.removeEventListener('keydown', handleWindowKeydown)
})
</script>

<style scoped>
.reply-segment {
  padding: 10px 12px;
  border-radius: 10px;
  border-left: 3px solid rgba(var(--v-theme-primary), 0.55);
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.session-entry-actions {
  display: flex;
  gap: 8px;
}

.session-entry-actions__primary {
  flex: 1 1 auto;
  min-width: 0;
}

.session-entry-actions__secondary {
  flex: 0 0 auto;
}

.session-preview {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pending-reply {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(var(--v-theme-primary), 0.18);
  border-left: 3px solid rgba(var(--v-theme-primary), 0.6);
  border-radius: 12px;
  background: rgba(var(--v-theme-primary), 0.08);
}

.pending-reply__content {
  min-width: 0;
  flex: 1;
}

.pending-reply__label {
  font-size: 12px;
  font-weight: 700;
  color: rgba(var(--v-theme-primary), 0.95);
}

.pending-reply__id {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.62);
}

.pending-reply__text {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), 0.82);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reply-segment__label {
  font-size: 12px;
  line-height: 1.2;
  color: rgba(var(--v-theme-on-surface), 0.62);
}

.reply-segment__id {
  margin-top: 2px;
  font-size: 13px;
  font-weight: 600;
}

.reply-segment__text {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), 0.86);
  white-space: pre-wrap;
}

.composer {
  min-height: 104px;
  max-height: 240px;
  overflow-y: auto;
  padding: 12px 14px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 14px;
  background: rgba(var(--v-theme-surface), 0.78);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  outline: none;
}

.composer-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.composer-attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: min(320px, 100%);
  padding: 8px 10px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.14);
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.composer-attachment-item--selected {
  border-color: rgba(var(--v-theme-primary), 0.45);
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.1);
}

.composer-attachment-index {
  min-width: 48px;
  font-size: 12px;
  font-weight: 700;
  color: rgba(var(--v-theme-on-surface), 0.72);
}

.composer-attachment-thumb {
  width: 44px;
  height: 44px;
  object-fit: cover;
  border-radius: 8px;
  cursor: zoom-in;
  flex-shrink: 0;
}

.composer-attachment-meta {
  min-width: 0;
  flex: 1;
}

.composer-attachment-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
}

.composer-attachment-size {
  margin-top: 2px;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.58);
}

.composer:empty::before {
  content: attr(data-placeholder);
  color: rgba(var(--v-theme-on-surface), 0.48);
}

.composer:focus {
  border-color: rgba(var(--v-theme-primary), 0.62);
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.1);
}

.composer--disabled {
  pointer-events: none;
  opacity: 0.65;
}

:deep(.composer-image-token) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 112px;
  min-height: 24px;
  margin: 0 4px;
  padding: 1px 7px;
  border: 1px solid rgba(var(--v-theme-primary), 0.32);
  border-radius: 8px;
  background: rgba(var(--v-theme-primary), 0.12);
  vertical-align: baseline;
  box-shadow:
    inset 0 0 0 1px rgba(var(--v-theme-surface), 0.35),
    0 1px 2px rgb(0 0 0 / 18%);
}

:deep(.composer-image-token--selected) {
  border-color: rgba(var(--v-theme-primary), 0.62);
  background: rgba(var(--v-theme-primary), 0.22);
  box-shadow:
    inset 0 0 0 1px rgba(var(--v-theme-surface), 0.45),
    0 0 0 2px rgba(var(--v-theme-primary), 0.14);
}

:deep(.composer-image-token__label) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  color: rgba(var(--v-theme-primary), 0.96);
}

:deep(.composer-image-token__remove) {
  width: 16px;
  height: 16px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  cursor: pointer;
  font-size: 10px;
  line-height: 1;
  flex-shrink: 0;
  color: rgba(var(--v-theme-on-surface), 0.76);
}

:deep(.composer-mention-token) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 140px;
  min-height: 24px;
  margin: 0 4px;
  padding: 1px 7px;
  border: 1px solid rgba(var(--v-theme-secondary), 0.28);
  border-radius: 999px;
  background: rgba(var(--v-theme-secondary), 0.12);
  vertical-align: baseline;
}

:deep(.composer-mention-token__label) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  color: rgba(var(--v-theme-secondary), 0.96);
}

:deep(.composer-mention-token__remove) {
  width: 16px;
  height: 16px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  cursor: pointer;
  font-size: 10px;
  line-height: 1;
  flex-shrink: 0;
  color: rgba(var(--v-theme-on-surface), 0.76);
}

.chat-image {
  display: block;
  max-width: min(680px, 72vw);
  width: auto;
  height: auto;
  border-radius: 8px;
  object-fit: contain;
  cursor: zoom-in;
  box-shadow: 0 8px 24px rgb(0 0 0 / 18%);
}

.image-message-card {
  display: inline-block;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.preview-card {
  background: rgba(var(--v-theme-surface), 0.96);
}

.preview-image-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  width: min(96vw, 1200px);
  height: min(82vh, 900px);
  overflow: hidden;
  padding: 24px;
}

.preview-meta {
  display: flex;
  gap: 16px;
}

.preview-image {
  display: block;
  max-width: min(92vw, 1120px);
  max-height: min(76vh, 820px);
  width: auto;
  height: auto;
  border-radius: 12px;
  transition: transform 0.08s ease-out;
  user-select: none;
}
</style>
