<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { useI18n } from 'vue-i18n'
import {
  fetchAdminChatDisputes,
  fetchAdminChatMessages,
  resolveAdminChatDispute,
  sendAdminChatMessage,
} from '../api'
import TextTranslateBlock from '../components/TextTranslateBlock.vue'

const { t } = useI18n()
const loading = ref(false)
const disputes = ref([])
const active = ref(null)
const messages = ref([])
const draft = ref('')
const error = ref('')
const sending = ref(false)
const loadingOlder = ref(false)
const hasMoreOlder = ref(false)

const MESSAGE_PAGE_SIZE = 50

const listEl = ref(null)

const virtualizer = useVirtualizer(
  computed(() => ({
    count: messages.value.length,
    getScrollElement: () => listEl.value,
    estimateSize: () => 96,
    overscan: 8,
    getItemKey: (index) => messages.value[index]?.id ?? index,
  }))
)
const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

const measureElement = (el) => {
  if (el) virtualizer.value.measureElement(el)
}

const formatMsgTime = (iso) => (iso || '').slice(0, 16).replace('T', ' ')

const scrollToBottom = async () => {
  await nextTick()
  const last = messages.value.length - 1
  if (last >= 0) virtualizer.value.scrollToIndex(last, { align: 'end' })
}

const loadDisputes = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchAdminChatDisputes({ page_size: 50 })
    disputes.value = res.data?.items || []
  } catch (e) {
    error.value = e?.message || t('chat.loadFailed')
  } finally {
    loading.value = false
  }
}

const openDispute = async (row) => {
  active.value = row
  messages.value = []
  hasMoreOlder.value = false
  try {
    const res = await fetchAdminChatMessages(row.id, { page_size: MESSAGE_PAGE_SIZE })
    messages.value = res.data?.items || []
    hasMoreOlder.value = (res.data?.pagination?.total_pages || 1) > 1
    await scrollToBottom()
  } catch (e) {
    error.value = e?.message || t('chat.loadFailed')
  }
}

/** 滚动到顶部时加载更早消息：使用 before_id 游标，prepend 后按锚点还原滚动位置。 */
const loadOlder = async () => {
  if (!active.value || loadingOlder.value || !hasMoreOlder.value) return
  const minId = messages.value[0]?.id
  if (!minId) return
  loadingOlder.value = true
  const el = listEl.value
  const anchor = { scrollHeight: el?.scrollHeight ?? 0, scrollTop: el?.scrollTop ?? 0 }
  try {
    const res = await fetchAdminChatMessages(active.value.id, {
      page_size: MESSAGE_PAGE_SIZE,
      before_id: minId,
    })
    const older = res.data?.items || []
    if (older.length) messages.value = [...older, ...messages.value]
    hasMoreOlder.value = (res.data?.pagination?.total_pages || 1) > 1
    await nextTick()
    if (el) el.scrollTop = anchor.scrollTop + (el.scrollHeight - anchor.scrollHeight)
  } catch (e) {
    error.value = e?.message || t('chat.loadFailed')
  } finally {
    loadingOlder.value = false
  }
}

const onMsgScroll = () => {
  const el = listEl.value
  if (!el || loadingOlder.value || !hasMoreOlder.value) return
  if (el.scrollTop <= 64) loadOlder()
}

const onSend = async () => {
  if (!active.value || !draft.value.trim() || sending.value) return
  sending.value = true
  try {
    const res = await sendAdminChatMessage(active.value.id, draft.value.trim())
    if (res.data) {
      messages.value.push(res.data)
      await scrollToBottom()
    }
    draft.value = ''
  } catch (e) {
    error.value = e?.message || t('chat.sendFailed')
  } finally {
    sending.value = false
  }
}

const onResolve = async () => {
  if (!active.value) return
  try {
    await resolveAdminChatDispute(active.value.id)
    active.value = null
    messages.value = []
    hasMoreOlder.value = false
    await loadDisputes()
  } catch (e) {
    error.value = e?.message || t('chat.resolveFailed')
  }
}

onMounted(loadDisputes)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h2>{{ t('chat.title') }}</h2>
      <el-button @click="loadDisputes">{{ t('common.refresh') }}</el-button>
    </div>
    <p class="hint">{{ t('chat.hint') }}</p>
    <el-alert v-if="error" :title="error" type="error" show-icon class="mb" @close="error = ''" />
    <div class="layout-grid">
      <el-card shadow="never">
        <template #header>{{ t('chat.openDisputes') }}</template>
        <el-skeleton v-if="loading" :rows="4" animated />
        <el-empty v-else-if="!disputes.length" :description="t('chat.empty')" />
        <el-table
          v-else
          :data="disputes"
          highlight-current-row
          @row-click="openDispute"
        >
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="quote_request_no" :label="t('chat.requestNo')" min-width="120" />
          <el-table-column prop="peer_display_name" :label="t('chat.parties')" min-width="160" />
          <el-table-column prop="dispute_reason" :label="t('chat.reason')" min-width="140" show-overflow-tooltip />
        </el-table>
      </el-card>
      <el-card shadow="never" class="thread">
        <template #header>
          <div class="thread-head">
            <span>{{ active ? `#${active.id}` : t('chat.select') }}</span>
            <el-button v-if="active" type="warning" size="small" @click="onResolve">
              {{ t('chat.resolve') }}
            </el-button>
          </div>
        </template>
        <template v-if="active">
          <p v-if="loadingOlder" class="load-older">{{ t('common.loading') }}</p>
          <div ref="listEl" class="msgs" @scroll.passive="onMsgScroll">
            <div
              v-if="messages.length"
              class="msg-spacer"
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
                <div class="msg" :class="messages[vr.index].sender_role">
                  <div class="meta">
                    {{ messages[vr.index].sender_role }} · {{ formatMsgTime(messages[vr.index].created_at) }}
                  </div>
                  <div v-if="messages[vr.index].message_type === 'order_card'" class="order-card-readonly">
                    <div class="order-tag">{{ t('chat.orderCardTag') }}</div>
                    <div class="order-no">{{ messages[vr.index].payload?.order_no || '—' }}</div>
                    <div v-if="messages[vr.index].payload?.status" class="order-status">
                      {{ messages[vr.index].payload.status }}
                    </div>
                    <div v-if="messages[vr.index].payload?.project_title">
                      {{ messages[vr.index].payload.project_title }}
                    </div>
                    <div v-if="messages[vr.index].body" class="order-note">{{ messages[vr.index].body }}</div>
                  </div>
                  <div v-else>{{ messages[vr.index].body }}</div>
                  <TextTranslateBlock
                    v-if="messages[vr.index].message_type !== 'order_card'"
                    :conversation-id="active.id"
                    :message-id="messages[vr.index].id"
                    :text="messages[vr.index].body"
                  />
                  <div
                    v-if="messages[vr.index].body_original && messages[vr.index].body_original !== messages[vr.index].body"
                    class="original"
                  >
                    {{ t('chat.original') }}: {{ messages[vr.index].body_original }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div v-if="active" class="composer">
          <el-input
            v-model="draft"
            type="textarea"
            :rows="2"
            :placeholder="t('chat.placeholder')"
          />
          <el-button type="primary" :loading="sending" @click="onSend">{{ t('chat.send') }}</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.hint { color: #6b7280; margin-bottom: 1rem; }
.mb { margin-bottom: 1rem; }
.layout-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 1rem;
}
.thread-head { display: flex; justify-content: space-between; align-items: center; }
.msgs {
  max-height: 480px;
  overflow: auto;
  position: relative;
  margin-bottom: 0.75rem;
}
.load-older { text-align: center; color: #6b7280; font-size: 12px; margin: 0 0 0.25rem; }
.msg-spacer { position: relative; width: 100%; }
.msg-virt {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  padding-bottom: 0.75rem;
  box-sizing: border-box;
}
.msg {
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}
.msg.platform { background: #eff6ff; border-color: #bfdbfe; }
.meta { font-size: 12px; color: #6b7280; margin-bottom: 0.25rem; }
.original { margin-top: 0.35rem; font-size: 12px; color: #b45309; }
.order-card-readonly {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.5rem 0.65rem;
  background: #fff;
}
.order-tag { font-size: 12px; font-weight: 600; color: #334155; }
.order-no { font-weight: 700; margin-top: 0.15rem; }
.order-status { font-size: 12px; color: #b45309; margin-top: 0.15rem; }
.order-note { margin-top: 0.35rem; font-size: 13px; white-space: pre-wrap; }
.composer { display: grid; gap: 0.5rem; }
@media (max-width: 960px) {
  .layout-grid { grid-template-columns: 1fr; }
}
</style>
