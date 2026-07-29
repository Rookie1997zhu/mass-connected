<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  sending: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const { t } = useI18n()
const draft = ref('')

const onSubmit = () => {
  const body = draft.value.trim()
  if (!body || props.sending) return
  emit('send', body)
}

/** 发送成功后由父组件调用，清空输入框 */
const clearDraft = () => {
  draft.value = ''
}

defineExpose({ clearDraft })
</script>

<template>
  <form class="composer" @submit.prevent="onSubmit">
    <input
      v-model="draft"
      type="text"
      maxlength="4000"
      :placeholder="t('chat.placeholder')"
      @keydown.enter.exact.prevent="onSubmit"
    />
    <button type="submit" class="send-btn" :disabled="sending || !draft.trim()">
      {{ t('chat.send') }}
    </button>
  </form>
</template>

<style scoped lang="scss">
.composer {
  display: flex;
  gap: 0.55rem;
  padding: 0.75rem 0.9rem 0.9rem;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}

.composer input {
  flex: 1;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 0.6rem 0.95rem;
  font: inherit;
  background: #f8fafc;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;

  &:focus {
    outline: none;
    border-color: var(--color-steel, #64748b);
    background: #fff;
    box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.15);
  }
}

.send-btn {
  border: 0;
  border-radius: 999px;
  padding: 0.55rem 1.05rem;
  background: #0f172a;
  color: #fff;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;

  &:hover:not(:disabled) { background: #1e293b; }
  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}
</style>
