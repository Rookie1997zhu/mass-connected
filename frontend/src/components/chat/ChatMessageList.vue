<script setup>
import { computed, nextTick, ref } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { useI18n } from 'vue-i18n'
import TextTranslateBlock from '../TextTranslateBlock.vue'
import OrderReminderCard from '../OrderReminderCard.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  role: { type: String, required: true },
  conversationId: { type: [Number, String], default: null },
  currentUserId: { type: [Number, String], default: null },
  loadingMessages: { type: Boolean, default: false },
  loadingOlder: { type: Boolean, default: false },
  hasMoreOlder: { type: Boolean, default: true },
})

const emit = defineEmits(['load-more', 'card-navigate'])

const { t } = useI18n()
const listEl = ref(null)

const virtualizer = useVirtualizer(
  computed(() => ({
    count: props.messages.length,
    getScrollElement: () => listEl.value,
    estimateSize: () => 88,
    overscan: 8,
    getItemKey: (index) => props.messages[index]?.id ?? index,
  }))
)

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

const measureElement = (el) => {
  if (!el) return
  virtualizer.value.measureElement(el)
}

const formatMsgTime = (iso) => {
  const s = (iso || '').slice(0, 16).replace('T', ' ')
  return s.length > 11 ? s.slice(11) : s
}

/** 滚动到底部（发送/收到新消息后调用） */
const scrollToBottom = async () => {
  await nextTick()
  const last = props.messages.length - 1
  if (last < 0) return
  virtualizer.value.scrollToIndex(last, { align: 'end' })
}

/** 加载更早消息前，捕获滚动锚点，避免 prepend 后跳动 */
const getScrollAnchor = () => {
  const el = listEl.value
  return { scrollHeight: el?.scrollHeight ?? 0, scrollTop: el?.scrollTop ?? 0 }
}

const restoreScrollAnchor = async (anchor) => {
  if (!anchor) return
  await nextTick()
  const el = listEl.value
  if (el) {
    el.scrollTop = anchor.scrollTop + (el.scrollHeight - anchor.scrollHeight)
  }
}

const onMsgScroll = () => {
  const el = listEl.value
  if (!el || props.loadingOlder || !props.hasMoreOlder) return
  if (el.scrollTop > 64) return
  const minId = props.messages[0]?.id
  if (minId) emit('load-more', minId)
}

const onCardNavigate = () => {
  emit('card-navigate')
}

defineExpose({ scrollToBottom, getScrollAnchor, restoreScrollAnchor })
</script>

<template>
  <div ref="listEl" class="msg-list" @scroll.passive="onMsgScroll">
    <p v-if="loadingMessages" class="muted center">{{ t('common.loading') }}</p>
    <div
      v-if="messages.length"
      class="msg-virt-spacer"
      :style="{ height: `${totalSize}px` }"
    >
      <div
        v-for="vr in virtualRows"
        :key="messages[vr.index].id"
        :data-index="vr.index"
        :ref="measureElement"
        class="msg-virt"
        :style="{ transform: `translateY(${vr.start}px)` }"
      >
        <div
          class="msg"
          :class="{
            mine: messages[vr.index].sender_id === currentUserId,
            platform: messages[vr.index].sender_role === 'platform',
            card: messages[vr.index].message_type === 'order_card',
          }"
        >
          <OrderReminderCard
            v-if="messages[vr.index].message_type === 'order_card'"
            :message="messages[vr.index]"
            :role="role"
            @navigate="onCardNavigate"
          />
          <template v-else>
            <p class="msg-body">{{ messages[vr.index].body }}</p>
            <small v-if="messages[vr.index].has_contact_hint" class="hint">
              {{ t('chat.contactMasked') }}
            </small>
          </template>
          <div class="msg-foot">
            <TextTranslateBlock
              v-if="messages[vr.index].message_type !== 'order_card'"
              context-type="chat"
              compact
              :role="role"
              :conversation-id="conversationId"
              :message-id="messages[vr.index].id"
              :text="messages[vr.index].body"
            />
            <time class="msg-time">{{ formatMsgTime(messages[vr.index].created_at) }}</time>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.msg-list {
  flex: 1;
  overflow: auto;
  padding: 1rem 0.9rem 1.15rem;
  background:
    radial-gradient(ellipse at top left, rgba(148, 163, 184, 0.12), transparent 45%),
    linear-gradient(180deg, #eef2f6 0%, #e8edf3 100%);
}

.msg-virt-spacer {
  width: 100%;
  position: relative;
}

.msg-virt {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  padding-bottom: 0.65rem;
  box-sizing: border-box;
}

.msg {
  max-width: min(78%, 420px);
  margin-right: auto;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 14px 14px 14px 4px;
  padding: 0.55rem 0.7rem 0.45rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.msg.mine {
  margin-left: auto;
  margin-right: 0;
  background: linear-gradient(160deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: #93c5fd;
  border-radius: 14px 14px 4px 14px;
}

.msg.platform {
  margin-left: auto;
  margin-right: auto;
  max-width: 88%;
  background: #f8fafc;
  border-style: dashed;
  font-style: italic;
  color: #475569;
  border-radius: 10px;
}

.msg.card {
  background: transparent;
  border: 0;
  box-shadow: none;
  padding: 0;
  max-width: min(88%, 360px);
}

.msg-body {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.9rem;
  line-height: 1.45;
  color: #0f172a;
}

.hint {
  display: block;
  color: #c2410c;
  margin-top: 0.3rem;
  font-size: 0.7rem;
}

.msg-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.15rem;
  min-height: 1rem;
}

.msg-time {
  color: #94a3b8;
  font-size: 0.65rem;
  flex-shrink: 0;
  margin-left: auto;
}

.muted { color: #64748b; font-size: 0.875rem; }
.center { text-align: center; margin: 1rem 0; }

@media (max-width: 720px) {
  .msg { max-width: 88%; }
}
</style>
