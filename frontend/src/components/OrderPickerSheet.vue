<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchRemindableOrders, sendChatOrderReminder } from '../api'
import { resolveApiMessage } from '../utils/apiErrors'

const props = defineProps({
  open: { type: Boolean, default: false },
  role: { type: String, required: true },
  conversationId: { type: [Number, String], required: true },
})

const emit = defineEmits(['close', 'sent', 'error'])

const { t } = useI18n()
const loading = ref(false)
const sending = ref(false)
const items = ref([])
const page = ref(1)
const totalPages = ref(1)
const q = ref('')
const status = ref('')
const selectedId = ref(null)
const note = ref('')

const statusOptions = [
  '',
  'pending_confirm',
  'confirmed',
  'in_production',
  'completed',
  'cancelled',
]

const load = async ({ reset = false } = {}) => {
  if (!props.conversationId) return
  if (reset) {
    page.value = 1
    items.value = []
  }
  loading.value = true
  try {
    const res = await fetchRemindableOrders(props.role, props.conversationId, {
      q: q.value.trim() || undefined,
      status: status.value || undefined,
      page: page.value,
      page_size: 20,
    })
    const next = res.data?.items || []
    items.value = reset ? next : [...items.value, ...next]
    totalPages.value = res.data?.pagination?.total_pages || 1
  } catch (e) {
    emit('error', resolveApiMessage(e, t, 'chat.orderPickerLoadFailed'))
  } finally {
    loading.value = false
  }
}

const onSearch = () => load({ reset: true })

const loadMore = () => {
  if (page.value >= totalPages.value || loading.value) return
  page.value += 1
  load()
}

const select = (row) => {
  selectedId.value = row.production_order_id
}

const selected = () => items.value.find((r) => r.production_order_id === selectedId.value)

const onSend = async () => {
  if (!selectedId.value || sending.value) return
  sending.value = true
  try {
    const res = await sendChatOrderReminder(props.role, props.conversationId, {
      production_order_id: selectedId.value,
      note: note.value.trim(),
    })
    emit('sent', res.data)
    emit('close')
  } catch (e) {
    emit('error', resolveApiMessage(e, t, 'chat.orderRemindFailed'))
  } finally {
    sending.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      q.value = ''
      status.value = ''
      selectedId.value = null
      note.value = ''
      load({ reset: true })
    }
  },
)

onMounted(() => {
  if (props.open) load({ reset: true })
})
</script>

<template>
  <div v-if="open" class="picker-overlay" @click.self="emit('close')">
    <div class="picker-sheet" role="dialog" aria-modal="true">
      <header class="picker-head">
        <strong>{{ t('chat.remindOrder') }}</strong>
        <button type="button" class="picker-close" @click="emit('close')">×</button>
      </header>
      <div class="picker-filters">
        <input
          v-model="q"
          type="search"
          :placeholder="t('chat.orderSearchPlaceholder')"
          @keydown.enter.prevent="onSearch"
        />
        <select v-model="status" @change="onSearch">
          <option v-for="s in statusOptions" :key="s || 'all'" :value="s">
            {{ s ? t(`chat.orderStatus.${s}`) : t('chat.orderStatusAll') }}
          </option>
        </select>
        <button type="button" class="btn-ghost" @click="onSearch">{{ t('chat.orderSearch') }}</button>
      </div>
      <div class="picker-list">
        <p v-if="loading && !items.length" class="muted">{{ t('common.loading') }}</p>
        <p v-else-if="!items.length" class="muted">{{ t('chat.orderPickerEmpty') }}</p>
        <button
          v-for="row in items"
          :key="row.production_order_id"
          type="button"
          class="picker-item"
          :class="{ selected: selectedId === row.production_order_id }"
          @click="select(row)"
        >
          <div class="picker-item-top">
            <span class="picker-no">{{ row.order_no }}</span>
            <span v-if="row.is_current" class="current-badge">{{ t('chat.orderCurrent') }}</span>
          </div>
          <div class="picker-meta">
            <span>{{ t(`chat.orderStatus.${row.status}`) }}</span>
            <span v-if="row.project_title"> · {{ row.project_title }}</span>
            <span v-if="row.quote_request_no"> · {{ row.quote_request_no }}</span>
          </div>
        </button>
        <button
          v-if="page < totalPages"
          type="button"
          class="load-more"
          :disabled="loading"
          @click="loadMore"
        >
          {{ t('chat.orderLoadMore') }}
        </button>
      </div>
      <div v-if="selected()" class="picker-preview">
        <div class="preview-title">{{ selected().order_no }}</div>
        <textarea
          v-model="note"
          rows="2"
          maxlength="2000"
          :placeholder="t('chat.orderNotePlaceholder')"
        />
        <button type="button" class="send-btn" :disabled="sending" @click="onSend">
          {{ sending ? t('common.loading') : t('chat.orderSendRemind') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.picker-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.picker-sheet {
  width: 100%;
  max-height: 78%;
  background: #fff;
  border-radius: 14px 14px 0 0;
  display: flex;
  flex-direction: column;
  box-shadow: 0 -8px 28px rgba(15, 23, 42, 0.15);
}

.picker-head {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.picker-close {
  margin-left: auto;
  border: 0;
  background: transparent;
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
}

.picker-filters {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.4rem;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid #eef2f6;

  input,
  select {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0.4rem 0.55rem;
    font: inherit;
    font-size: 0.82rem;
  }
}

.btn-ghost {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 8px;
  padding: 0.35rem 0.55rem;
  font-size: 0.75rem;
  cursor: pointer;
}

.picker-list {
  flex: 1;
  overflow: auto;
  padding: 0.5rem 0.75rem;
  min-height: 140px;
}

.picker-item {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  padding: 0.55rem 0.65rem;
  margin-bottom: 0.45rem;
  cursor: pointer;

  &.selected {
    border-color: #64748b;
    background: #eef2f6;
  }
}

.picker-item-top {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.picker-no {
  font-weight: 700;
  font-size: 0.86rem;
}

.current-badge {
  font-size: 0.65rem;
  color: #1d4ed8;
  background: #dbeafe;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.picker-meta {
  margin-top: 0.2rem;
  font-size: 0.72rem;
  color: #64748b;
}

.load-more {
  width: 100%;
  border: 0;
  background: transparent;
  color: #475569;
  padding: 0.5rem;
  cursor: pointer;
  font-size: 0.78rem;
}

.picker-preview {
  border-top: 1px solid #e2e8f0;
  padding: 0.75rem 0.85rem 0.9rem;
  display: grid;
  gap: 0.5rem;
}

.preview-title {
  font-weight: 600;
  font-size: 0.88rem;
}

.picker-preview textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.5rem 0.6rem;
  font: inherit;
  resize: vertical;
}

.send-btn {
  border: 0;
  border-radius: 999px;
  padding: 0.55rem 1rem;
  background: #0f172a;
  color: #fff;
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.muted {
  color: #64748b;
  font-size: 0.85rem;
  padding: 0.5rem;
}
</style>
