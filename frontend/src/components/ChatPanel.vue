<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  fetchChatConversations,
  fetchChatMessages,
  fetchChatUnreadCount,
  markChatConversationRead,
  openChatConversation,
  openChatDispute,
  resolveChatDispute,
  sendChatMessage,
} from '../api'
import { createChatSocket } from '../utils/chatWs'
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
const draft = ref('')
const loadingList = ref(false)
const loadingMessages = ref(false)
const sending = ref(false)
const error = ref('')
const wsStatus = ref('closed')
const disputeReason = ref('')
const showDisputeForm = ref(false)
const listEl = ref(null)

let socket = null
let lastMsgId = 0

const activeConversation = computed(() =>
  conversations.value.find((c) => c.id === activeId.value) || null
)

const loadConversations = async () => {
  loadingList.value = true
  try {
    const res = await fetchChatConversations(role.value, { page_size: 50 })
    conversations.value = res.data?.items || []
  } catch (e) {
    error.value = e?.message || t('chat.loadFailed')
  } finally {
    loadingList.value = false
  }
}

const loadMessages = async (conversationId, { afterId } = {}) => {
  if (!conversationId) return
  loadingMessages.value = !afterId
  try {
    const params = afterId ? { after_id: afterId } : { page_size: 50 }
    const res = await fetchChatMessages(role.value, conversationId, params)
    const items = res.data?.items || []
    if (afterId) {
      const known = new Set(messages.value.map((m) => m.id))
      items.forEach((m) => {
        if (!known.has(m.id)) messages.value.push(m)
      })
    } else {
      messages.value = items
    }
    if (messages.value.length) {
      lastMsgId = messages.value[messages.value.length - 1].id
    }
    await markChatConversationRead(role.value, conversationId)
    const unreadRes = await fetchChatUnreadCount(role.value)
    emit('unread-change', unreadRes.data?.count ?? 0)
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  } catch (e) {
    error.value = e?.message || t('chat.loadFailed')
  } finally {
    loadingMessages.value = false
  }
}

const selectConversation = async (id) => {
  activeId.value = id
  messages.value = []
  lastMsgId = 0
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
    error.value = e?.message || t('chat.openFailed')
  }
}

const onSend = async () => {
  const body = draft.value.trim()
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
    draft.value = ''
    await loadConversations()
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  } catch (e) {
    error.value = e?.message || e?.code || t('chat.sendFailed')
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
    error.value = e?.message || t('chat.disputeFailed')
  }
}

const onResolveDispute = async () => {
  if (!activeId.value) return
  try {
    await resolveChatDispute(role.value, activeId.value)
    await loadConversations()
  } catch (e) {
    error.value = e?.message || t('chat.disputeFailed')
  }
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
        await nextTick()
        if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
      }
    } else {
      await loadConversations()
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
  const token = window.__memberAccessToken
  if (!token || !auth.isLoggedIn) return
  socket?.close()
  socket = createChatSocket({
    token,
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
        <strong>{{ t('chat.title') }}</strong>
        <span class="ws-dot" :class="wsStatus" :title="wsStatus" />
        <button type="button" class="chat-close" @click="emit('close')">×</button>
      </header>
      <p class="chat-safety">{{ t('chat.safetyTip') }}</p>
      <div class="chat-body">
        <aside class="chat-list">
          <p v-if="loadingList" class="muted">{{ t('common.loading') }}</p>
          <p v-else-if="!conversations.length" class="muted">{{ t('chat.empty') }}</p>
          <button
            v-for="c in conversations"
            :key="c.id"
            type="button"
            class="conv-item"
            :class="{ active: c.id === activeId }"
            @click="selectConversation(c.id)"
          >
            <span class="conv-name">{{ c.peer_display_name || c.quote_request_no }}</span>
            <span class="conv-preview">{{ c.last_message_preview || c.quote_request_no }}</span>
            <span v-if="c.unread" class="conv-unread">{{ c.unread > 99 ? '99+' : c.unread }}</span>
          </button>
        </aside>
        <section class="chat-main">
          <div v-if="!activeId" class="muted pad">{{ t('chat.selectConversation') }}</div>
          <template v-else>
            <div class="chat-toolbar">
              <span>{{ activeConversation?.peer_display_name }}</span>
              <template v-if="activeConversation?.dispute_status === 'open'">
                <span class="dispute-badge">{{ t('chat.disputeOpen') }}</span>
                <button type="button" class="btn btn-sm btn-secondary" @click="onResolveDispute">
                  {{ t('chat.resolveDispute') }}
                </button>
              </template>
              <button
                v-else
                type="button"
                class="btn btn-sm btn-secondary"
                @click="showDisputeForm = !showDisputeForm"
              >
                {{ t('chat.requestIntervention') }}
              </button>
            </div>
            <div v-if="showDisputeForm" class="dispute-form">
              <textarea v-model="disputeReason" rows="2" :placeholder="t('chat.disputeReason')" />
              <button type="button" class="btn btn-sm btn-primary" @click="onOpenDispute">
                {{ t('chat.submitDispute') }}
              </button>
            </div>
            <div ref="listEl" class="msg-list">
              <p v-if="loadingMessages" class="muted">{{ t('common.loading') }}</p>
              <div
                v-for="m in messages"
                :key="m.id"
                class="msg"
                :class="{
                  mine: m.sender_id === auth.user?.id,
                  platform: m.sender_role === 'platform',
                }"
              >
                <p class="msg-body">{{ m.body }}</p>
                <small v-if="m.has_contact_hint" class="hint">{{ t('chat.contactMasked') }}</small>
                <small class="msg-time">{{ (m.created_at || '').slice(0, 16).replace('T', ' ') }}</small>
              </div>
            </div>
            <form class="composer" @submit.prevent="onSend">
              <input
                v-model="draft"
                type="text"
                maxlength="4000"
                :placeholder="t('chat.placeholder')"
                @keydown.enter.exact.prevent="onSend"
              />
              <button type="submit" class="btn btn-primary btn-sm" :disabled="sending">
                {{ t('chat.send') }}
              </button>
            </form>
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
  background: rgba(15, 23, 42, 0.35);
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
  align-items: stretch;
}
.chat-panel {
  width: min(920px, 100%);
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e2e8f0;
}
.chat-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  background: #0f172a;
  color: #fff;
}
.chat-close {
  margin-left: auto;
  background: transparent;
  border: 0;
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
}
.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}
.ws-dot.open { background: #22c55e; }
.ws-dot.connecting { background: #eab308; }
.ws-dot.error, .ws-dot.closed { background: #f87171; }
.chat-safety {
  margin: 0;
  padding: 0.65rem 1rem;
  font-size: 0.8rem;
  line-height: 1.45;
  background: #fff7ed;
  color: #9a3412;
  border-bottom: 1px solid #fed7aa;
}
.chat-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 240px 1fr;
}
.chat-list {
  border-right: 1px solid #e2e8f0;
  overflow: auto;
  background: #fff;
}
.conv-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.15rem 0.5rem;
  width: 100%;
  text-align: left;
  padding: 0.75rem;
  border: 0;
  border-bottom: 1px solid #f1f5f9;
  background: transparent;
  cursor: pointer;
}
.conv-item.active { background: #e2e8f0; }
.conv-name { font-weight: 600; font-size: 0.9rem; grid-column: 1; }
.conv-preview {
  grid-column: 1;
  font-size: 0.75rem;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-unread {
  grid-row: 1 / span 2;
  align-self: center;
  background: #dc2626;
  color: #fff;
  border-radius: 999px;
  min-width: 1.25rem;
  text-align: center;
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
}
.chat-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
}
.dispute-badge {
  font-size: 0.75rem;
  color: #b45309;
  background: #fef3c7;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}
.dispute-form {
  padding: 0.5rem 0.75rem;
  display: grid;
  gap: 0.5rem;
  background: #fffbeb;
}
.msg-list {
  flex: 1;
  overflow: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.msg {
  max-width: 80%;
  align-self: flex-start;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.5rem 0.65rem;
}
.msg.mine {
  align-self: flex-end;
  background: #dbeafe;
  border-color: #93c5fd;
}
.msg.platform {
  align-self: center;
  background: #f1f5f9;
  font-style: italic;
}
.msg-body { margin: 0; white-space: pre-wrap; word-break: break-word; }
.hint { display: block; color: #c2410c; margin-top: 0.25rem; }
.msg-time { color: #94a3b8; }
.composer {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}
.composer input {
  flex: 1;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0.5rem 0.65rem;
}
.chat-error {
  margin: 0;
  padding: 0.5rem 1rem;
  color: #b91c1c;
  background: #fef2f2;
}
.muted { color: #64748b; font-size: 0.875rem; }
.pad { padding: 1rem; }
@media (max-width: 720px) {
  .chat-body { grid-template-columns: 1fr; }
  .chat-list { max-height: 30vh; }
}
</style>
