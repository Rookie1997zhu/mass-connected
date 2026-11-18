<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  sending: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'attach'])

const { t } = useI18n()
const draft = ref('')
const fileInput = ref(null)

const onSubmit = () => {
  const body = draft.value.trim()
  if (!body || props.sending || props.readonly) return
  emit('send', body)
}

const onPickFile = () => {
  if (props.sending || props.readonly) return
  fileInput.value?.click()
}

const onFileChange = (e) => {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || props.sending || props.readonly) return
  emit('attach', file)
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
      ref="fileInput"
      type="file"
      class="file-input"
      @change="onFileChange"
    />
    <button
      type="button"
      class="attach-btn"
      :disabled="sending || readonly"
      :title="t('chat.attach')"
      @click="onPickFile"
    >
      {{ t('chat.attachShort') }}
    </button>
    <input
      v-model="draft"
      type="text"
      maxlength="4000"
      :disabled="readonly"
      :placeholder="readonly ? t('chat.readonlyPlaceholder') : t('chat.placeholder')"
      @keydown.enter.exact.prevent="onSubmit"
    />
    <button type="submit" class="send-btn" :disabled="sending || readonly || !draft.trim()">
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

.file-input {
  display: none;
}

.attach-btn {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 0.55rem 0.75rem;
  background: #f8fafc;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

.composer input[type='text'] {
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
