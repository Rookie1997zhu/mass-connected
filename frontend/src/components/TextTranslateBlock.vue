<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  translateChatMessage,
  translateMemberProjectText,
  translateMemberQuoteText,
  translateMemberRfqText,
  translateSupplierProjectText,
  translateSupplierQuoteRequestText,
  translateSupplierQuoteText,
} from '../api'
import { pollChatTranslateJob } from '../utils/pollJob'
import { resolveApiMessage } from '../utils/apiErrors'

const props = defineProps({
  // Legacy project API: projectId + role
  projectId: { type: [Number, String], default: null },
  // Generalized: contextType + contextId + role
  contextType: { type: String, default: '' }, // 'project' | 'rfq' | 'quote' | 'quoteRequest' | 'chat'
  contextId: { type: [Number, String], default: null },
  conversationId: { type: [Number, String], default: null },
  messageId: { type: [Number, String], default: null },
  role: { type: String, required: true }, // 'member' | 'supplier'
  text: { type: String, default: '' },
  /** 聊天等紧凑场景：文字链样式，避免大按钮 */
  compact: { type: Boolean, default: false },
})

const { t, locale } = useI18n()
const loading = ref(false)
const error = ref('')
const translated = ref('')

const isCompact = computed(() => props.compact || props.contextType === 'chat')

watch(
  () => [props.text, props.messageId],
  () => {
    translated.value = ''
    error.value = ''
  },
)

const resolveTranslateApi = () => {
  const type = props.contextType || (props.projectId != null ? 'project' : '')
  if (type === 'chat') {
    if (props.conversationId == null || props.messageId == null) return null
    return (data) => translateChatMessage(props.role, props.conversationId, props.messageId, data)
  }
  const id = props.contextId ?? props.projectId
  if (!type || id == null) return null
  if (props.role === 'supplier') {
    if (type === 'project') return (data) => translateSupplierProjectText(id, data)
    if (type === 'quoteRequest') return (data) => translateSupplierQuoteRequestText(id, data)
    if (type === 'quote') return (data) => translateSupplierQuoteText(id, data)
    if (type === 'rfq') return (data) => translateSupplierQuoteRequestText(id, data)
  } else {
    if (type === 'project') return (data) => translateMemberProjectText(id, data)
    if (type === 'rfq') return (data) => translateMemberRfqText(id, data)
    if (type === 'quote') return (data) => translateMemberQuoteText(id, data)
  }
  return null
}

const onTranslate = async () => {
  const source = (props.text || '').trim()
  if (!source) return
  const api = resolveTranslateApi()
  if (!api) return
  loading.value = true
  error.value = ''
  try {
    const payload =
      props.contextType === 'chat'
        ? { target_lang: locale.value }
        : { text: source, target_lang: locale.value }
    const res = await api(payload)
    const data = res.data || {}
    if (props.contextType === 'chat' && !data.translated_text && data.job_id) {
      const jobData = await pollChatTranslateJob(props.role, data.job_id)
      translated.value = jobData.result?.translated_text || ''
    } else {
      translated.value = data.translated_text || ''
    }
    if (!translated.value) {
      error.value = t('aiTranslate.translateFailed')
    }
  } catch (e) {
    const code = e?.code || e?.response?.data?.code
    if (code === 'TRANSLATE_NOT_CONFIGURED') {
      error.value = t('aiTranslate.notConfigured')
    } else {
      error.value = resolveApiMessage(e, t, 'aiTranslate.translateFailed')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="(text || '').trim()" class="translate-block" :class="{ compact: isCompact }">
    <button
      type="button"
      :class="isCompact ? 'translate-link' : 'btn btn-secondary btn-sm'"
      :disabled="loading"
      @click="onTranslate"
    >
      {{ loading ? t('aiTranslate.translating') : t('aiTranslate.translate') }}
    </button>
    <p v-if="error" class="translate-error">{{ error }}</p>
    <p v-if="translated" class="translate-result">{{ translated }}</p>
  </div>
</template>

<style scoped lang="scss">
.translate-block {
  margin-top: 0.35rem;

  &.compact {
    margin-top: 0;
    display: inline-flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
    min-width: 0;
    flex: 1;
  }
}

.translate-link {
  display: inline;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-steel, #475569);
  font-size: 0.7rem;
  line-height: 1.2;
  font-weight: 500;
  letter-spacing: 0.01em;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
  text-decoration-color: color-mix(in srgb, var(--color-steel, #475569) 35%, transparent);

  &:hover:not(:disabled) {
    color: var(--color-ink, #0f172a);
    text-decoration-color: currentColor;
  }

  &:disabled {
    opacity: 0.55;
    cursor: wait;
  }
}

.translate-result {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  opacity: 0.85;
  white-space: pre-wrap;
  padding: 0.4rem 0.5rem;
  background: var(--color-steel-muted, rgba(0, 0, 0, 0.04));
  border-radius: 4px;

  .compact & {
    margin-top: 0.25rem;
    font-size: 0.78rem;
    line-height: 1.45;
    padding: 0.3rem 0.4rem;
    border-radius: 6px;
    border-left: 2px solid color-mix(in srgb, var(--color-steel, #64748b) 45%, transparent);
    background: rgba(15, 23, 42, 0.04);
  }
}

.translate-error {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: #b91c1c;

  .compact & {
    margin-top: 0.2rem;
    font-size: 0.68rem;
  }
}
</style>
