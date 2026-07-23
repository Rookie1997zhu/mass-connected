<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  fetchAdminChatDisputes,
  fetchAdminChatMessages,
  resolveAdminChatDispute,
  sendAdminChatMessage,
} from '../api'

const { t } = useI18n()
const loading = ref(false)
const disputes = ref([])
const active = ref(null)
const messages = ref([])
const draft = ref('')
const error = ref('')
const sending = ref(false)

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
  try {
    const res = await fetchAdminChatMessages(row.id, { page_size: 100 })
    messages.value = res.data?.items || []
  } catch (e) {
    error.value = e?.message || t('chat.loadFailed')
  }
}

const onSend = async () => {
  if (!active.value || !draft.value.trim() || sending.value) return
  sending.value = true
  try {
    const res = await sendAdminChatMessage(active.value.id, draft.value.trim())
    if (res.data) messages.value.push(res.data)
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
        <div v-if="active" class="msgs">
          <div
            v-for="m in messages"
            :key="m.id"
            class="msg"
            :class="m.sender_role"
          >
            <div class="meta">{{ m.sender_role }} · {{ (m.created_at || '').slice(0, 16).replace('T', ' ') }}</div>
            <div>{{ m.body }}</div>
            <div v-if="m.body_original && m.body_original !== m.body" class="original">
              {{ t('chat.original') }}: {{ m.body_original }}
            </div>
          </div>
        </div>
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
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
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
.composer { display: grid; gap: 0.5rem; }
@media (max-width: 960px) {
  .layout-grid { grid-template-columns: 1fr; }
}
</style>
