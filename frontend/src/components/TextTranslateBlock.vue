<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { translateMemberProjectText, translateSupplierProjectText } from '../api'

const props = defineProps({
  projectId: { type: [Number, String], required: true },
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

const onTranslate = async () => {
  const source = (props.text || '').trim()
  if (!source) return
  loading.value = true
  error.value = ''
  try {
    const api =
      props.role === 'supplier' ? translateSupplierProjectText : translateMemberProjectText
    const res = await api(props.projectId, {
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
