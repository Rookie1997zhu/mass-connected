<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  translateMemberProjectText,
  translateMemberQuoteText,
  translateMemberRfqText,
  translateSupplierProjectText,
  translateSupplierQuoteRequestText,
  translateSupplierQuoteText,
} from '../api'

const props = defineProps({
  // Legacy project API: projectId + role
  projectId: { type: [Number, String], default: null },
  // Generalized: contextType + contextId + role
  contextType: { type: String, default: '' }, // 'project' | 'rfq' | 'quote' | 'quoteRequest'
  contextId: { type: [Number, String], default: null },
  role: { type: String, required: true }, // 'member' | 'supplier'
  text: { type: String, default: '' },
})

const { t, locale } = useI18n()
const loading = ref(false)
const error = ref('')
const translated = ref('')

watch(
  () => props.text,
  () => {
    translated.value = ''
    error.value = ''
  },
)

const resolveTranslateApi = () => {
  const type = props.contextType || (props.projectId != null ? 'project' : '')
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
    const res = await api({
      text: source,
      target_lang: locale.value,
    })
    translated.value = res.data?.translated_text || ''
    if (!translated.value) {
      error.value = t('aiTranslate.translateFailed')
    }
  } catch (e) {
    const code = e?.code || e?.response?.data?.code
    if (code === 'TRANSLATE_NOT_CONFIGURED') {
      error.value = t('aiTranslate.notConfigured')
    } else {
      error.value = e.message || t('aiTranslate.translateFailed')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="(text || '').trim()" class="translate-block">
    <button
      type="button"
      class="btn btn-secondary btn-sm"
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
}
.translate-result {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  opacity: 0.85;
  white-space: pre-wrap;
  padding: 0.4rem 0.5rem;
  background: var(--color-steel-muted, rgba(0, 0, 0, 0.04));
  border-radius: 4px;
}
.translate-error {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: #b91c1c;
}
</style>
