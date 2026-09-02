<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { verifyEmailResend } from '../api'
import { resolveApiMessage } from '../utils/apiErrors'

const { t } = useI18n()
const resending = ref(false)
const resent = ref(false)
const error = ref('')

const onResend = async () => {
  error.value = ''
  resending.value = true
  try {
    await verifyEmailResend()
    resent.value = true
  } catch (e) {
    if (e?.code === 'EMAIL_ALREADY_VERIFIED') {
      resent.value = true
      return
    }
    error.value = resolveApiMessage(e, t, 'register.resendFailed')
  } finally {
    resending.value = false
  }
}
</script>

<template>
  <PageShell centered>
    <div class="verify-card">
      <h1 class="page-title">{{ t('register.verifySentTitle') }}</h1>
      <p>{{ t('register.verifySent') }}</p>
      <p class="hint">{{ t('register.verifySentHint') }}</p>
      <p v-if="resent" class="success">{{ t('register.resendSuccess') }}</p>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="resending" @click="onResend">
          {{ resending ? t('register.resending') : t('register.resend') }}
        </button>
        <RouterLink to="/my/rfqs" class="btn btn-secondary">{{ t('register.verifyContinue') }}</RouterLink>
      </div>
    </div>
  </PageShell>
</template>

<style scoped>
.verify-card {
  max-width: 32rem;
  margin: 0 auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.hint {
  color: var(--color-muted, #666);
  font-size: 0.95rem;
}
.success {
  color: #15803d;
}
.error {
  color: #b91c1c;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: center;
  margin-top: 0.5rem;
}
</style>
