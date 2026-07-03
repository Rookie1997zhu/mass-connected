<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { acceptQuote, downloadRfqQuotePdf, fetchMyRfq } from '../../api'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const rfq = ref(null)
const loading = ref(true)
const message = ref('')
const successMessage = ref('')

const load = async () => {
  const res = await fetchMyRfq(route.params.id)
  rfq.value = res.data
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const onDownloadPdf = async () => {
  const res = await downloadRfqQuotePdf(rfq.value.id)
  const blob = new Blob([res], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${rfq.value.rfq_no}-comparison.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

const onAccept = async (quoteId) => {
  message.value = ''
  successMessage.value = ''
  try {
    const res = await acceptQuote(rfq.value.id, quoteId)
    const orderNo = res.data?.production_order?.order_no
    successMessage.value = orderNo
      ? t('productionOrder.created', { orderNo })
      : t('myRfqs.acceptSuccess')
    await load()
    if (orderNo) {
      setTimeout(() => router.push('/my/production-orders'), 1500)
    }
  } catch (e) {
    message.value = e.message || t('rfq.acceptFailed')
  }
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="rfq">
      <h1 class="page-title">{{ rfq.rfq_no }}</h1>
      <p class="rfq-status-line">{{ t('common.status') }}: <strong>{{ rfq.status }}</strong></p>

      <dl class="detail-grid">
        <div><dt>{{ t('rfq.stepProcess') }}</dt><dd>{{ rfq.service_category_name }}</dd></div>
        <div><dt>{{ t('rfq.quantity') }}</dt><dd>{{ rfq.quantity }}</dd></div>
        <div><dt>{{ t('rfq.material') }}</dt><dd>{{ rfq.material || '—' }}</dd></div>
        <div><dt>{{ t('rfq.tolerance') }}</dt><dd>{{ rfq.tolerance || '—' }}</dd></div>
        <div><dt>{{ t('rfq.surfaceFinish') }}</dt><dd>{{ rfq.surface_finish || '—' }}</dd></div>
        <div><dt>{{ t('rfq.targetDate') }}</dt><dd>{{ rfq.target_delivery_date || '—' }}</dd></div>
        <div class="full"><dt>{{ t('rfq.remark') }}</dt><dd>{{ rfq.remark || '—' }}</dd></div>
      </dl>

      <h2 class="section-sub">{{ t('rfq.attachments') }}</h2>
      <p v-if="!rfq.attachments?.length" class="page-empty">—</p>
      <ul v-else class="att-list">
        <li v-for="a in rfq.attachments" :key="a.id">
          <a :href="a.url" target="_blank" rel="noopener">{{ a.file_name }}</a>
        </li>
      </ul>

      <h2 class="section-sub">{{ t('myRfqs.plans') }}</h2>
      <button v-if="rfq.plans?.length" type="button" class="btn btn-secondary btn-sm mb" @click="onDownloadPdf">{{ t('myRfqs.downloadPdf') }}</button>
      <p v-if="successMessage" class="page-message page-message--success">{{ successMessage }}</p>
      <p v-if="message" class="page-message page-message--error">{{ message }}</p>
      <p v-if="!rfq.plans?.length" class="page-empty">{{ t('myRfqs.noPlans') }}</p>
      <table v-else-if="rfq.plans.length > 1" class="quote-table mb">
        <thead>
          <tr>
            <th></th>
            <th v-for="p in rfq.plans" :key="p.id">{{ t('myRfqs.plan') }} {{ p.plan_label || p.id }}</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>{{ t('rfq.price') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.currency }} {{ Number(p.price_amount).toLocaleString() }}</td></tr>
          <tr><td>{{ t('myRfqs.unitPrice') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.unit_price ? Number(p.unit_price).toLocaleString() : '—' }}</td></tr>
          <tr><td>{{ t('myRfqs.moldFee') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.mold_fee ? Number(p.mold_fee).toLocaleString() : '—' }}</td></tr>
          <tr><td>{{ t('myRfqs.sampleFee') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.sample_fee ? Number(p.sample_fee).toLocaleString() : '—' }}</td></tr>
          <tr><td>{{ t('myRfqs.moq') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.moq || '—' }}</td></tr>
          <tr><td>{{ t('rfq.leadTime') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.lead_time_days }}</td></tr>
          <tr><td>{{ t('myRfqs.paymentTerms') }}</td><td v-for="p in rfq.plans" :key="p.id">{{ p.payment_terms || '—' }}</td></tr>
        </tbody>
      </table>
      <div v-if="rfq.plans?.length" class="plan-grid">
        <article v-for="p in rfq.plans" :key="p.id" class="plan-card" :class="{ 'plan-card--accepted': p.status === 'accepted' }">
          <div class="plan-head">
            <span class="plan-label">{{ t('myRfqs.plan') }} {{ p.plan_label || '-' }}</span>
            <span v-if="p.status === 'accepted'" class="accepted">✓ {{ t('myRfqs.confirmed') }}</span>
          </div>
          <p class="plan-price">{{ p.currency }} {{ Number(p.price_amount).toLocaleString() }}</p>
          <ul class="plan-meta">
            <li>{{ t('rfq.leadTime') }}: {{ p.lead_time_days }}</li>
            <li>{{ t('rfq.validUntil') }}: {{ p.valid_until || '—' }}</li>
            <li v-if="p.moq">{{ t('myRfqs.moq') }}: {{ p.moq }}</li>
            <li v-if="p.payment_terms">{{ t('myRfqs.paymentTerms') }}: {{ p.payment_terms }}</li>
            <li v-if="p.note">{{ p.note }}</li>
          </ul>
          <button
            v-if="p.status === 'sent'"
            type="button"
            class="btn btn-primary btn-sm"
            @click="onAccept(p.id)"
          >
            {{ t('myRfqs.confirmPlan') }}
          </button>
        </article>
      </div>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.rfq-status-line { margin-bottom: var(--space-lg); }
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md) var(--space-xl);
  margin: 0 0 var(--space-2xl);

  .full { grid-column: 1 / -1; }
  dt { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text); opacity: 0.6; }
  dd { margin: 0.25rem 0 0; font-weight: 500; }
}
.section-sub { font-size: 1.125rem; margin: var(--space-xl) 0 var(--space-md); }
.att-list { padding-left: 1.2rem; a { color: var(--color-steel); } }
.plan-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-lg); }
.plan-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); display: flex; flex-direction: column; gap: var(--space-sm); }
.plan-card--accepted { border-color: var(--color-steel); background: var(--color-steel-muted); }
.plan-head { display: flex; justify-content: space-between; align-items: center; }
.plan-label { font-weight: 700; font-size: 1rem; }
.plan-price { font-size: 1.375rem; font-weight: 700; margin: 0; }
.plan-meta { list-style: none; padding: 0; margin: 0; font-size: 0.875rem; opacity: 0.75; display: flex; flex-direction: column; gap: 0.25rem; }
.quote-table {
  width: 100%;
  border-collapse: collapse;

  th, td {
    text-align: left;
    padding: var(--space-sm) var(--space-md);
    border-bottom: 1px solid var(--color-border);
    font-size: 0.9375rem;
  }
  th { font-size: 0.75rem; text-transform: uppercase; color: var(--color-text); opacity: 0.6; }
}
.mb { margin-bottom: var(--space-md); }
@media (max-width: 640px) {
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
