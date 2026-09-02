<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../components/PageShell.vue'
import { verifyEmailConfirm } from '../api'
import { useAuthStore } from '../stores/auth'
import { resolveApiMessage } from '../utils/apiErrors'

const { t } = useI18n()
const route = useRoute()
const auth = useAuthStore()

const status = ref('loading')
const errorMessage = ref('')

onMounted(async () => {
  const token = (route.query.token || '').trim()
  if (!token) {
    status.value = 'missing'
    return
  }
  try {
    const res = await verifyEmailConfirm(token)
    if (res.data?.user) {
      auth.updateUser(res.data.user)
    } else {
      auth.markEmailVerified()
    }
    status.value = 'success'
  } catch (e) {
    if (e?.code === 'EMAIL_VERIFY_TOKEN_EXPIRED') {
      status.value = 'expired'
    } else {
      status.value = 'invalid'
      errorMessage.value = resolveApiMessage(e, t, 'register.verifyFailed')
    }
  }
})
</script>

<template>
  <PageShell centered>
    <div v-if="status === 'loading'" class="verify-card">
      <p>{{ t('register.verifyProcessing') }}</p>
    </div>
    <div v-else-if="status === 'success'" class="verify-card">
      <h1 class="page-title">{{ t('register.verifySuccessTitle') }}</h1>
      <p>{{ t('register.verifySuccess') }}</p>
      <RouterLink to="/my/rfqs" class="btn btn-primary">{{ t('register.verifyContinue') }}</RouterLink>
    </div>
    <div v-else-if="status === 'expired'" class="verify-card">
      <h1 class="page-title">{{ t('register.verifyExpiredTitle') }}</h1>
      <p>{{ t('register.verifyExpired') }}</p>
      <RouterLink to="/verify-email/sent" class="btn btn-primary">{{ t('register.resend') }}</RouterLink>
    </div>
    <div v-else class="verify-card">
      <h1 class="page-title">{{ t('register.verifyFailedTitle') }}</h1>
      <p>{{ errorMessage || t('register.verifyFailed') }}</p>
      <RouterLink to="/verify-email/sent" class="btn btn-primary">{{ t('register.resend') }}</RouterLink>
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
  gap: 1rem;
}
</style>
