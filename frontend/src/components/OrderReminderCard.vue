<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

const props = defineProps({
  message: { type: Object, required: true },
  role: { type: String, required: true }, // member | supplier
  interactive: { type: Boolean, default: true },
})

const emit = defineEmits(['navigate'])

const { t } = useI18n()
const router = useRouter()

const payload = computed(() => props.message?.payload || {})
const note = computed(() => (props.message?.body || '').trim())

const statusLabel = computed(() => {
  const status = payload.value.status
  if (!status) return ''
  const key = `chat.orderStatus.${status}`
  const label = t(key)
  return label === key ? status : label
})

const onOpen = () => {
  if (!props.interactive) return
  const projectId = payload.value.project_id
  const poId = payload.value.production_order_id
  const qrId = payload.value.quote_request_id
  let path = ''
  if (projectId) {
    path =
      props.role === 'supplier'
        ? `/supplier/projects/${projectId}`
        : `/my/projects/${projectId}`
  } else if (props.role === 'member' && poId) {
    path = `/my/production-orders/${poId}`
  } else if (props.role === 'supplier' && qrId) {
    path = `/supplier/quote-requests/${qrId}`
  }
  if (!path) return
  emit('navigate', path)
  router.push(path)
}
</script>

<template>
  <button
    type="button"
    class="order-card"
    :class="{ interactive }"
    :disabled="!interactive"
    @click="onOpen"
  >
    <div class="order-card-top">
      <span class="order-card-tag">{{ t('chat.orderCardTag') }}</span>
      <span v-if="statusLabel" class="order-card-status">{{ statusLabel }}</span>
    </div>
    <div class="order-card-no">{{ payload.order_no || '—' }}</div>
    <div v-if="payload.project_title" class="order-card-project">{{ payload.project_title }}</div>
    <div v-if="payload.quote_request_no" class="order-card-meta">{{ payload.quote_request_no }}</div>
    <p v-if="note" class="order-card-note">{{ note }}</p>
  </button>
</template>

<style scoped lang="scss">
.order-card {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 0.55rem 0.65rem;
  background: #fff;
  color: inherit;
  font: inherit;
  cursor: default;
}

.order-card.interactive {
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;

  &:hover {
    border-color: #64748b;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
  }
}

.order-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  margin-bottom: 0.25rem;
}

.order-card-tag {
  font-size: 0.65rem;
  font-weight: 600;
  color: #334155;
  letter-spacing: 0.02em;
}

.order-card-status {
  font-size: 0.65rem;
  color: #b45309;
  background: #fef3c7;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.order-card-no {
  font-size: 0.88rem;
  font-weight: 700;
  color: #0f172a;
}

.order-card-project,
.order-card-meta {
  margin-top: 0.15rem;
  font-size: 0.72rem;
  color: #64748b;
}

.order-card-note {
  margin: 0.4rem 0 0;
  font-size: 0.78rem;
  line-height: 1.4;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
