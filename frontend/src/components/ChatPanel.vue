<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  createChatWsTicket,
  fetchChatConversations,
  fetchChatMessages,
  fetchChatUnreadCount,
  markChatConversationRead,
  openChatConversation,
  openChatDispute,
  resolveChatDispute,
  sendChatMessage,
} from '../api'
import ChatMessageList from './chat/ChatMessageList.vue'
import ChatComposer from './chat/ChatComposer.vue'
import OrderPickerSheet from './OrderPickerSheet.vue'
import { createChatSocket } from '../utils/chatWs'
import { resolveApiMessage } from '../utils/apiErrors'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  open: { type: Boolean, default: false },
  /** 外部指定打开某 quote_request 的会话 */
  quoteRequestId: { type: [Number, String], default: null },
  conversationId: { type: [Number, String], default: null },
})

const emit = defineEmits(['close', 'unread-change', 'update:quoteRequestId', 'update:conversationId'])

const { t } = useI18n()
const auth = useAuthStore()

const role = computed(() => (auth.user?.role === 'factory' || auth.isSupplier ? 'supplier' : 'member'))
const conversations = ref([])
const activeId = ref(null)
const messages = ref([])
const loadingList = ref(false)
const loadingMessages = ref(false)
const loadingOlder = ref(false)
const hasMoreOlder = ref(true)
const sending = ref(false)
const error = ref('')
const wsStatus = ref('closed')
const disputeReason = ref('')
const showDisputeForm = ref(false)
const showOrderPicker = ref(false)
const messageListRef = ref(null)
const composerRef = ref(null)

let socket = null
let lastMsgId = 0

const activeConversation = computed(() =>
  conversations.value.find((c) => c.id === activeId.value) || null
)

const peerInitial = computed(() => {
  const name = (activeConversation.value?.peer_display_name || '').trim()
  return name ? name.slice(0, 1).toUpperCase() : '?'
})

const convInitial = (c) => {
  const name = (c?.peer_display_name || c?.quote_request_no || '').trim()
  return name ? name.slice(0, 1).toUpperCase() : '?'
}

const previewFromMessage = (msg) => {
  if (msg?.message_type === 'order_card') {
    const orderNo = msg?.payload?.order_no || ''
    return orderNo ? `[订单] ${orderNo}` : '[订单]'
  }
  return String(msg?.body || '').slice(0, 120)
}

const bumpConversationLocal = (conversationId, msg, { incrementUnread = false, clearUnread = false } = {}) => {
  const idx = conversations.value.findIndex((c) => c.id === conversationId)
  if (idx < 0) return
  const conv = { ...conversations.value[idx] }
  if (msg) conv.last_message_preview = previewFromMessage(msg)
  if (clearUnread) conv.unread = 0
  else if (incrementUnread) conv.unread = (conv.unread || 0) + 1
  const next = conversations.value.slice()
  next.splice(idx, 1)
  next.unshift(conv)
  conversations.value = next
}

const loadConversations = async () => {
  loadingList.value = true
  try {
    const res = await fetchChatConversations(role.value, { page_size: 50 })
    conversations.value = res.data?.items || []
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'chat.loadFailed')
  } finally {
    loadingList.value = false
  }
}

const loadMessages = async (conversationId, { afterId, beforeId } = {}) => {
  if (!conversationId) return
  if (beforeId) {
    if (loadingOlder.value || !hasMoreOlder.value) return
    loadingOlder.value = true
  } else {
    loadingMessages.value = !afterId
  }
  try {
    const params = afterId
      ? { after_id: afterId }
      : beforeId
        ? { before_id: beforeId, page_size: 50 }
        : { page_size: 50 }
    const res = await fetchChatMessages(role.value, conversationId, params)
    const items = res.data?.items || []
    if (beforeId) {
      if (!items.length) {
        hasMoreOlder.value = false
        return
      }
      if (items.length < 50) hasMoreOlder.value = false
      const known = new Set(messages.value.map((m) => m.id))
      const older = items.filter((m) => !known.has(m.id))
      if (!older.length) {
        hasMoreOlder.value = false
        return
      }
      const anchor = messageListRef.value?.getScrollAnchor()
      messages.value = [...older, ...messages.value]
      await messageListRef.value?.restoreScrollAnchor(anchor)
    } else if (afterId) {
      const known = new Set(messages.value.map((m) => m.id))
      items.forEach((m) => {
        if (!known.has(m.id)) messages.value.push(m)
      })
      if (messages.value.length) {
        lastMsgId = messages.value[messages.value.length - 1].id
      }
      if (items.length) await messageListRef.value?.scrollToBottom()
    } else {
      messages.value = items
      hasMoreOlder.value = items.length >= 50
      if (messages.value.length) {
        lastMsgId = messages.value[messages.value.length - 1].id
      }
      await markChatConversationRead(role.value, conversationId)
      const unreadRes = await fetchChatUnreadCount(role.value)
      emit('unread-change', unreadRes.data?.count ?? 0)
      bumpConversationLocal(conversationId, null, { clearUnread: true })
      await messageListRef.value?.scrollToBottom()
    }
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'chat.loadFailed')
  } finally {
    loadingMessages.value = false
    loadingOlder.value = false
  }
}

const onLoadMore = (minId) => {
  if (!activeId.value) return
  loadMessages(activeId.value, { beforeId: minId })
}

const selectConversation = async (id) => {
  activeId.value = id
  messages.value = []
  lastMsgId = 0
  hasMoreOlder.value = true
  showOrderPicker.value = false
  await loadMessages(id)
}

const openByQuoteRequest = async (qrId) => {
  if (!qrId) return
  try {
    const res = await openChatConversation(role.value, Number(qrId))
    const conv = res.data
    await loadConversations()
    if (conv?.id) await selectConversation(conv.id)
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'chat.openFailed')
  }
}

const onSend = async (body) => {
  if (!body || !activeId.value || sending.value) return
  sending.value = true
  error.value = ''
  try {
    const res = await sendChatMessage(role.value, activeId.value, body)
    const msg = res.data
    if (msg && !messages.value.some((m) => m.id === msg.id)) {
      messages.value.push(msg)
      lastMsgId = msg.id
    }
    composerRef.value?.clearDraft()
    if (msg) bumpConversationLocal(activeId.value, msg, { clearUnread: true })
    await messageListRef.value?.scrollToBottom()
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'chat.sendFailed')
  } finally {
    sending.value = false
  }
}

const onOpenDispute = async () => {
  if (!activeId.value) return
  try {
    await openChatDispute(role.value, activeId.value, disputeReason.value)
    showDisputeForm.value = false
    disputeReason.value = ''
    await loadConversations()
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'chat.disputeFailed')
  }
}

const onResolveDispute = async () => {
  if (!activeId.value) return
  try {
    await resolveChatDispute(role.value, activeId.value)
    await loadConversations()
  } catch (e) {
    error.value = resolveApiMessage(e, t, 'chat.disputeFailed')
  }
}

const onOrderReminderSent = async (msg) => {
  if (msg && !messages.value.some((m) => m.id === msg.id)) {
    messages.value.push(msg)
    lastMsgId = msg.id
  }
  if (msg) bumpConversationLocal(activeId.value, msg, { clearUnread: true })
  await messageListRef.value?.scrollToBottom()
}

const onCardNavigate = () => {
  emit('close')
}

const handleWsEvent = async (data) => {
  const event = data?.event
  const payload = data?.payload || {}
  if (event === 'new_message') {
    if (payload.conversation_id === activeId.value) {
      if (!messages.value.some((m) => m.id === payload.id)) {
        messages.value.push(payload)
        lastMsgId = payload.id
        await markChatConversationRead(role.value, activeId.value)
        bumpConversationLocal(payload.conversation_id, payload, { clearUnread: true })
        await messageListRef.value?.scrollToBottom()
      }
    } else if (payload.conversation_id) {
      bumpConversationLocal(payload.conversation_id, payload, { incrementUnread: true })
    }
    if (payload.unread_total != null) emit('unread-change', payload.unread_total)
  }
  if (event === 'unread_updated' && payload.count != null) {
    emit('unread-change', payload.count)
  }
  if (event === 'dispute_updated' || event === 'conversation_updated') {
    await loadConversations()
  }
}

const connectWs = () => {
  if (!auth.isLoggedIn) return
  socket?.close()
  socket = createChatSocket({
    fetchTicket: async () => {
      const res = await createChatWsTicket(role.value)
      return res?.data?.ticket || null
    },
    onEvent: handleWsEvent,
    onStatus: (s) => {
      wsStatus.value = s
      if (s === 'open' && activeId.value && lastMsgId) {
        loadMessages(activeId.value, { afterId: lastMsgId })
      }
    },
  })
}

watch(
  () => props.open,
  async (v) => {
    if (v) {
      error.value = ''
      await loadConversations()
      connectWs()
      if (props.quoteRequestId) await openByQuoteRequest(props.quoteRequestId)
      else if (props.conversationId) await selectConversation(Number(props.conversationId))
    } else {
      socket?.close()
      socket = null
    }
  }
)

watch(
  () => props.quoteRequestId,
  async (id) => {
    if (props.open && id) await openByQuoteRequest(id)
  }
)

onMounted(async () => {
  if (props.open) {
    await loadConversations()
    connectWs()
  }
})

onUnmounted(() => {
  socket?.close()
})

defineExpose({ openByQuoteRequest, selectConversation, loadConversations })
</script>

<template>
  <div v-if="open" class="chat-overlay" @click.self="emit('close')">
    <div class="chat-panel" role="dialog" aria-modal="true">
      <header class="chat-head">
        <div class="chat-head-title">
          <strong>{{ t('chat.title') }}</strong>
          <span class="ws-pill">
            <span class="ws-dot" :class="wsStatus" />
            <span class="ws-label">{{ wsStatus === 'open' ? 'Online' : wsStatus }}</span>
          </span>
        </div>
        <button type="button" class="chat-close" :aria-label="t('common.close')" @click="emit('close')">
          ×
        </button>
      </header>
      <p class="chat-safety">{{ t('chat.safetyTip') }}</p>
      <div class="chat-body">
        <aside class="chat-list">
          <p v-if="loadingList" class="muted pad-sm">{{ t('common.loading') }}</p>
          <p v-else-if="!conversations.length" class="muted pad-sm">{{ t('chat.empty') }}</p>
          <button
            v-for="c in conversations"
            :key="c.id"
            type="button"
            class="conv-item"
            :class="{ active: c.id === activeId }"
            @click="selectConversation(c.id)"
          >
            <span class="conv-avatar" aria-hidden="true">{{ convInitial(c) }}</span>
            <span class="conv-text">
              <span class="conv-name">{{ c.peer_display_name || c.quote_request_no }}</span>
              <span class="conv-preview">{{ c.last_message_preview || c.quote_request_no }}</span>
            </span>
            <span v-if="c.unread" class="conv-unread">{{ c.unread > 99 ? '99+' : c.unread }}</span>
          </button>
        </aside>
        <section class="chat-main">
          <div v-if="!activeId" class="empty-thread">
            <p class="muted">{{ t('chat.selectConversation') }}</p>
          </div>
          <template v-else>
            <div class="chat-toolbar">
              <span class="peer-avatar" aria-hidden="true">{{ peerInitial }}</span>
              <div class="peer-meta">
                <span class="peer-name">{{ activeConversation?.peer_display_name }}</span>
                <span v-if="activeConversation?.quote_request_no" class="peer-sub">
                  {{ activeConversation.quote_request_no }}
                </span>
              </div>
              <div class="toolbar-actions">
                <button type="button" class="btn-ghost" @click="showOrderPicker = true">
                  {{ t('chat.remindOrder') }}
                </button>
                <template v-if="activeConversation?.dispute_status === 'open'">
                  <span class="dispute-badge">{{ t('chat.disputeOpen') }}</span>
                  <button type="button" class="btn-ghost" @click="onResolveDispute">
                    {{ t('chat.resolveDispute') }}
                  </button>
                </template>
                <button
                  v-else
                  type="button"
                  class="btn-ghost"
                  @click="showDisputeForm = !showDisputeForm"
                >
                  {{ t('chat.requestIntervention') }}
                </button>
              </div>
            </div>
            <div v-if="showDisputeForm" class="dispute-form">
              <textarea v-model="disputeReason" rows="2" :placeholder="t('chat.disputeReason')" />
              <button type="button" class="btn btn-sm btn-primary" @click="onOpenDispute">
                {{ t('chat.submitDispute') }}
              </button>
            </div>
            <div class="thread-wrap">
              <ChatMessageList
                ref="messageListRef"
                :messages="messages"
                :role="role"
                :conversation-id="activeId"
                :current-user-id="auth.user?.id"
                :loading-messages="loadingMessages"
                :loading-older="loadingOlder"
                :has-more-older="hasMoreOlder"
                @load-more="onLoadMore"
                @card-navigate="onCardNavigate"
              />
              <OrderPickerSheet
                :open="showOrderPicker"
                :role="role"
                :conversation-id="activeId"
                @close="showOrderPicker = false"
                @sent="onOrderReminderSent"
                @error="(msg) => (error = msg)"
              />
            </div>
            <ChatComposer ref="composerRef" :sending="sending" @send="onSend" />
          </template>
        </section>
      </div>
      <p v-if="error" class="chat-error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chat-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(2px);
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
  align-items: stretch;
  animation: chat-fade-in 0.18s ease-out;
}

@keyframes chat-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.chat-panel {
  width: min(940px, 100%);
  background: #f4f6f8;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #d8dee6;
  box-shadow: -12px 0 40px rgba(15, 23, 42, 0.12);
  animation: chat-slide-in 0.22s ease-out;
}

@keyframes chat-slide-in {
  from { transform: translateX(18px); opacity: 0.85; }
  to { transform: translateX(0); opacity: 1; }
}

.chat-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.9rem 1.1rem;
  background:
    linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%);
  color: #fff;
}

.chat-head-title {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;

  strong {
    font-size: 1rem;
    letter-spacing: 0.01em;
  }
}

.ws-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 0.68rem;
  color: #cbd5e1;
  text-transform: capitalize;
}

.chat-close {
  margin-left: auto;
  width: 2rem;
  height: 2rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 0;
  color: #fff;
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover { background: rgba(255, 255, 255, 0.18); }
}

.ws-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
  flex-shrink: 0;
}
.ws-dot.open { background: #4ade80; box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.2); }
.ws-dot.connecting { background: #facc15; }
.ws-dot.error, .ws-dot.closed { background: #f87171; }

.chat-safety {
  margin: 0;
  padding: 0.55rem 1.1rem;
  font-size: 0.75rem;
  line-height: 1.45;
  background: linear-gradient(90deg, #fff7ed, #ffedd5);
  color: #9a3412;
  border-bottom: 1px solid #fdba74;
}

.chat-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 260px 1fr;
}

.chat-list {
  border-right: 1px solid #e2e8f0;
  overflow: auto;
  background: #fafbfc;
}

.conv-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.55rem;
  align-items: center;
  width: 100%;
  text-align: left;
  padding: 0.7rem 0.85rem;
  border: 0;
  border-bottom: 1px solid #eef2f6;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover { background: #f1f5f9; }
  &.active {
    background: #e8eef5;
    box-shadow: inset 3px 0 0 var(--color-steel, #475569);
  }
}

.conv-avatar,
.peer-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: #334155;
  background: linear-gradient(145deg, #e2e8f0, #cbd5e1);
  flex-shrink: 0;
}

.conv-text {
  min-width: 0;
  display: grid;
  gap: 0.12rem;
}

.conv-name {
  font-weight: 600;
  font-size: 0.86rem;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-preview {
  font-size: 0.72rem;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-unread {
  background: #dc2626;
  color: #fff;
  border-radius: 999px;
  min-width: 1.15rem;
  text-align: center;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.12rem 0.32rem;
}

.chat-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #eef2f6;
  position: relative;
}

.thread-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
}

.empty-thread {
  flex: 1;
  display: grid;
  place-items: center;
  padding: 2rem;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.9rem;
  border-bottom: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
}

.peer-meta {
  min-width: 0;
  display: grid;
  gap: 0.05rem;
  flex: 1;
}

.peer-name {
  font-weight: 600;
  font-size: 0.92rem;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.peer-sub {
  font-size: 0.7rem;
  color: #64748b;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.btn-ghost {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  font-size: 0.72rem;
  padding: 0.28rem 0.55rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;

  &:hover {
    background: #f8fafc;
    border-color: #94a3b8;
  }
}

.dispute-badge {
  font-size: 0.7rem;
  color: #b45309;
  background: #fef3c7;
  padding: 0.18rem 0.45rem;
  border-radius: 6px;
  font-weight: 600;
}

.dispute-form {
  padding: 0.65rem 0.9rem;
  display: grid;
  gap: 0.5rem;
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;

  textarea {
    width: 100%;
    border: 1px solid #fcd34d;
    border-radius: 8px;
    padding: 0.5rem 0.65rem;
    font: inherit;
    resize: vertical;
  }
}

.chat-error {
  margin: 0;
  padding: 0.5rem 1rem;
  color: #b91c1c;
  background: #fef2f2;
  font-size: 0.82rem;
}

.muted { color: #64748b; font-size: 0.875rem; }
.pad-sm { padding: 0.85rem; }

@media (max-width: 720px) {
  .chat-body { grid-template-columns: 1fr; }
  .chat-list { max-height: 28vh; }
  .ws-label { display: none; }
}
</style>
