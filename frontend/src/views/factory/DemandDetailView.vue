<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchDemandDetail, submitFactoryQuote } from '../../api'

const { t } = useI18n()
const route = useRoute()
const rfq = ref(null)
const loading = ref(true)
const message = ref('')
const error = ref('')
const quote = ref({ price_amount: '', lead_time_days: 7, valid_until: '', note: '' })

const load = async () => {
  const res = await fetchDemandDetail(route.params.id)
  rfq.value = res.data
}

onMounted(async () => {
  try {
    await load()
  } finally {
    loading.value = false
  }
})

const submit = async () => {
  error.value = ''
  message.value = ''
  try {
    await submitFactoryQuote(rfq.value.id, {
      price_amount: Number(quote.value.price_amount),
      currency: 'KRW',
      lead_time_days: Number(quote.value.lead_time_days),
      valid_until: quote.value.valid_until || null,
      note: quote.value.note,
    })
    message.value = t('demandHall.quoteSubmitted')
    await load()
  } catch (e) {
    error.value = e.message || t('demandHall.quoteFailed')
  }
}
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

      <section v-if="rfq.my_quote" class="card quote-existing">
        <h2>{{ t('demandHall.myQuote') }}</h2>
        <p>{{ t('rfq.price') }}: KRW {{ Number(rfq.my_quote.price_amount).toLocaleString() }}</p>
        <p>{{ t('common.status') }}: {{ rfq.my_quote.status }}</p>
      </section>

      <section v-else class="card quote-form">
        <h2>{{ t('demandHall.submitQuote') }}</h2>
        <p v-if="error" class="page-message page-message--error">{{ error }}</p>
        <p v-if="message" class="page-message page-message--success">{{ message }}</p>
        <label>{{ t('rfq.price') }} (KRW)<input v-model="quote.price_amount" type="number" min="1" required /></label>
        <label>{{ t('rfq.leadTime') }}<input v-model="quote.lead_time_days" type="number" min="1" required /></label>
        <label>{{ t('rfq.validUntil') }}<input v-model="quote.valid_until" type="date" /></label>
        <label>{{ t('rfq.note') }}<textarea v-model="quote.note" rows="3" /></label>
        <button type="button" class="btn btn-primary" @click="submit">{{ t('demandHall.submitQuote') }}</button>
      </section>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-md); margin-bottom: var(--space-xl); dt { font-size: 0.8125rem; color: var(--color-text-muted); } dd { margin: 0.25rem 0 0; font-weight: 500; } }
.section-sub { margin: var(--space-xl) 0 var(--space-md); }
.quote-form, .quote-existing { margin-top: var(--space-xl); padding: var(--space-lg); display: flex; flex-direction: column; gap: var(--space-md); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.875rem; } input, textarea { padding: 0.625rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
</style>
