<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { translateAdminChatMessage } from '../api'

const props = defineProps({
  conversationId: { type: [Number, String], required: true },
  messageId: { type: [Number, String], required: true },
  text: { type: String, default: '' },
})

const { t, locale } = useI18n()
const loading = ref(false)
const error = ref('')
const translated = ref('')

watch(
  () => [props.text, props.messageId],
  () => {
    translated.value = ''
    error.value = ''
  },
)

const onTranslate = async () => {
  const source = (props.text || '').trim()
  if (!source || props.conversationId == null || props.messageId == null) return
  loading.value = true
  error.value = ''
  try {
    const res = await translateAdminChatMessage(props.conversationId, props.messageId, {
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
    <el-button size="small" :loading="loading" @click="onTranslate">
      {{ loading ? t('aiTranslate.translating') : t('aiTranslate.translate') }}
    </el-button>
    <p v-if="error" class="translate-error">{{ error }}</p>
    <p v-if="translated" class="translate-result">{{ translated }}</p>
  </div>
</template>

<style scoped>
.translate-block {
  margin-top: 0.35rem;
}
.translate-result {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  opacity: 0.85;
  white-space: pre-wrap;
  padding: 0.4rem 0.5rem;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
}
.translate-error {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: #b91c1c;
}
</style>
