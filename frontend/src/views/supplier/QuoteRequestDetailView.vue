<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchSupplierQuoteRequest, submitSupplierQuote } from '../../api'

const { t } = useI18n()
const route = useRoute()
const data = ref(null)
const loading = ref(true)
const error = ref('')
const message = ref('')
const form = ref({
  price_amount: '', unit_price: '', mold_fee: '', sample_fee: '', moq: '',
  payment_terms: '', lead_time_days: 7, valid_until: '', note: '',
})

const load = async () => {
  const res = await fetchSupplierQuoteRequest(route.params.id)
  data.value = res.data
}

onMounted(async () => {
  try { await load() } finally { loading.value = false }
})

const submit = async () => {
  error.value = ''
  message.value = ''
  try {
    await submitSupplierQuote(route.params.id, {
      price_amount: Number(form.value.price_amount),
      unit_price: form.value.unit_price ? Number(form.value.unit_price) : null,
      mold_fee: form.value.mold_fee ? Number(form.value.mold_fee) : null,
      sample_fee: form.value.sample_fee ? Number(form.value.sample_fee) : null,
      moq: form.value.moq ? Number(form.value.moq) : null,
      payment_terms: form.value.payment_terms,
      currency: 'KRW',
      lead_time_days: Number(form.value.lead_time_days),
      valid_until: form.value.valid_until || null,
      note: form.value.note,
    })
    message.value = t('quoteRequest.submitted')
    await load()
  } catch (e) {
    error.value = e.message || t('demandHall.quoteFailed')
  }
}
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="data">
      <h1 class="page-title">{{ data.request_no }}</h1>
      <p class="page-lead">{{ data.rfq_no }} · {{ data.service_category_name }}</p>

      <dl class="detail-grid">
        <div><dt>{{ t('rfq.quantity') }}</dt><dd>{{ data.rfq_detail?.quantity }}</dd></div>
        <div><dt>{{ t('rfq.material') }}</dt><dd>{{ data.rfq_detail?.material || '—' }}</dd></div>
        <div><dt>{{ t('quoteRequest.deadline') }}</dt><dd>{{ data.deadline || '—' }}</dd></div>
        <div class="full"><dt>{{ t('quoteRequest.adminNote') }}</dt><dd>{{ data.admin_note || '—' }}</dd></div>
        <div class="full"><dt>{{ t('rfq.remark') }}</dt><dd>{{ data.rfq_detail?.remark || '—' }}</dd></div>
      </dl>

      <h2 class="section-sub">{{ t('rfq.attachments') }}</h2>
      <ul v-if="data.rfq_detail?.attachments?.length" class="att-list">
        <li v-for="a in data.rfq_detail.attachments" :key="a.id">
          <a :href="a.url" target="_blank" rel="noopener">{{ a.file_name }}</a>
        </li>
      </ul>
      <p v-else class="page-empty">—</p>

      <section v-if="data.my_quote" class="card quote-existing">
        <h2>{{ t('demandHall.myQuote') }}</h2>
        <p>{{ t('rfq.price') }}: KRW {{ Number(data.my_quote.price_amount).toLocaleString() }}</p>
        <p>{{ t('mypage.status') }}: {{ data.my_quote.status }}</p>
      </section>

      <section v-else class="card quote-form">
        <h2>{{ t('quoteRequest.submitQuote') }}</h2>
        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <p v-if="message" class="page-message page-message--success">{{ message }}</p>
        <label>{{ t('rfq.price') }} (KRW)<input v-model="form.price_amount" type="number" min="1" /></label>
        <label>{{ t('myRfqs.unitPrice') }}<input v-model="form.unit_price" type="number" min="0" /></label>
        <label>{{ t('myRfqs.moldFee') }}<input v-model="form.mold_fee" type="number" min="0" /></label>
        <label>{{ t('myRfqs.sampleFee') }}<input v-model="form.sample_fee" type="number" min="0" /></label>
        <label>{{ t('myRfqs.moq') }}<input v-model="form.moq" type="number" min="1" /></label>
        <label>{{ t('myRfqs.paymentTerms') }}<input v-model="form.payment_terms" type="text" /></label>
        <label>{{ t('rfq.leadTime') }}<input v-model="form.lead_time_days" type="number" min="1" /></label>
        <label>{{ t('rfq.validUntil') }}<input v-model="form.valid_until" type="date" /></label>
        <label>{{ t('rfq.note') }}<textarea v-model="form.note" rows="3" /></label>
        <button type="button" class="btn btn-primary" @click="submit">{{ t('quoteRequest.submitQuote') }}</button>
      </section>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md) var(--space-xl); margin: var(--space-lg) 0; .full { grid-column: 1 / -1; } dt { font-size: 0.75rem; text-transform: uppercase; opacity: 0.6; } dd { margin: 0.25rem 0 0; font-weight: 500; } }
.section-sub { font-size: 1.125rem; margin: var(--space-xl) 0 var(--space-md); }
.att-list { padding-left: 1.2rem; a { color: var(--color-steel); } }
.card { margin-top: var(--space-xl); padding: var(--space-lg); border: 1px solid var(--color-border); border-radius: var(--radius-md); }
.quote-form { display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } input, textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
</style>
