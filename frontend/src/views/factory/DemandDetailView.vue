<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchDemandDetail, grabDemand } from '../../api'
import { useAuthStore } from '../../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const rfq = ref(null)
const loading = ref(true)
const grabbing = ref(false)
const error = ref('')
const message = ref('')

const load = async () => {
  const res = await fetchDemandDetail(route.params.id)
  rfq.value = res.data
}

const goQuote = (quoteRequestId) => {
  router.push(`/supplier/quote-requests/${quoteRequestId}`)
}

const onGrab = async () => {
  if (!auth.isSupplier) return
  error.value = ''
  message.value = ''
  grabbing.value = true
  try {
    const res = await grabDemand(route.params.id)
    message.value = res.message || t('demandHall.grabSuccess')
    await load()
    if (res.data?.id) {
      goQuote(res.data.id)
    }
  } catch (e) {
    error.value = e.message || t('demandHall.grabFailed')
  } finally {
    grabbing.value = false
  }
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="rfq">
      <h1 class="page-title">{{ rfq.rfq_no }}</h1>
      <dl class="detail-grid">
        <div><dt>{{ t('rfq.stepProcess') }}</dt><dd>{{ rfq.service_category_name }}</dd></div>
        <div><dt>{{ t('rfq.quantity') }}</dt><dd>{{ rfq.quantity }}</dd></div>
        <div><dt>{{ t('rfq.material') }}</dt><dd>{{ rfq.material || '—' }}</dd></div>
        <div><dt>{{ t('rfq.tolerance') }}</dt><dd>{{ rfq.tolerance || '—' }}</dd></div>
        <div><dt>{{ t('rfq.surfaceFinish') }}</dt><dd>{{ rfq.surface_finish || '—' }}</dd></div>
        <div><dt>{{ t('rfq.targetDate') }}</dt><dd>{{ rfq.target_delivery_date || '—' }}</dd></div>
      </dl>

      <h2 class="section-sub">{{ t('rfq.attachments') }}</h2>
      <ul v-if="rfq.attachments?.length" class="att-list">
        <li v-for="a in rfq.attachments" :key="a.id">
          <a :href="a.url" target="_blank" rel="noopener">{{ a.file_name }}</a>
        </li>
      </ul>
      <p v-else class="page-empty">—</p>

      <section v-if="auth.isSupplier" class="card quote-hint">
        <h2>{{ t('demandHall.submitQuote') }}</h2>
        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <p v-if="message" class="page-message page-message--success">{{ message }}</p>

        <section v-if="rfq.my_quote" class="quote-existing">
          <p>{{ t('demandHall.myQuote') }}: KRW {{ Number(rfq.my_quote.price_amount).toLocaleString() }}</p>
          <p>{{ t('mypage.status') }}: {{ rfq.my_quote.status }}</p>
        </section>

        <template v-else-if="rfq.my_quote_request">
          <p class="page-lead">{{ t('demandHall.alreadyGrabbed') }}</p>
          <button type="button" class="btn btn-primary" @click="goQuote(rfq.my_quote_request.id)">
            {{ t('demandHall.goQuote') }}
          </button>
        </template>

        <template v-else>
          <p class="page-lead">{{ t('demandHall.grabHint') }}</p>
          <button type="button" class="btn btn-primary" :disabled="grabbing" @click="onGrab">
            {{ grabbing ? t('common.loading') : t('demandHall.grab') }}
          </button>
        </template>
      </section>

      <section v-else-if="!auth.isLoggedIn" class="card quote-hint">
        <p class="page-lead">{{ t('demandHall.quoteFactoryOnly') }}</p>
        <RouterLink to="/login" class="btn btn-primary">{{ t('nav.login') }}</RouterLink>
      </section>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-md); margin-bottom: var(--space-xl); dt { font-size: 0.8125rem; color: var(--color-text-muted); } dd { margin: 0.25rem 0 0; font-weight: 500; } }
.section-sub { margin: var(--space-xl) 0 var(--space-md); }
.quote-form, .quote-existing, .quote-hint { margin-top: var(--space-xl); padding: var(--space-lg); display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } input, textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.quote-hint .page-lead { margin: 0; }
</style>
