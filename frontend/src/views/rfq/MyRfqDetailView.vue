<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { acceptQuote, fetchMyRfq } from '../../api'

const { t } = useI18n()
const route = useRoute()
const rfq = ref(null)
const loading = ref(true)
const message = ref('')

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

const onAccept = async (quoteId) => {
  message.value = ''
  try {
    await acceptQuote(rfq.value.id, quoteId)
    await load()
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

      <h2 class="section-sub">{{ t('myRfqs.quotes') }}</h2>
      <p v-if="message" class="page-message page-message--error">{{ message }}</p>
      <p v-if="!rfq.quotes?.length" class="page-empty">{{ t('myRfqs.noQuotes') }}</p>
      <table v-else class="quote-table">
        <thead>
          <tr>
            <th>{{ t('myRfqs.supplier') }}</th>
            <th>{{ t('rfq.price') }}</th>
            <th>{{ t('rfq.leadTime') }}</th>
            <th>{{ t('rfq.validUntil') }}</th>
            <th>{{ t('rfq.note') }}</th>
            <th>{{ t('common.status') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="q in rfq.quotes" :key="q.id">
            <td>{{ q.supplier_name }} ({{ q.supplier_type === 'factory' ? t('myRfqs.factory') : t('myRfqs.platform') }})</td>
            <td>{{ q.currency }} {{ Number(q.price_amount).toLocaleString() }}</td>
            <td>{{ q.lead_time_days }}</td>
            <td>{{ q.valid_until || '—' }}</td>
            <td>{{ q.note || '—' }}</td>
            <td>{{ q.status }}</td>
            <td>
              <button
                v-if="q.status === 'sent'"
                type="button"
                class="btn btn-primary btn-sm"
                @click="onAccept(q.id)"
              >
                {{ t('myRfqs.accept') }}
              </button>
              <span v-else-if="q.status === 'accepted'" class="accepted">✓</span>
            </td>
          </tr>
        </tbody>
      </table>
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
.accepted { color: var(--color-steel); font-weight: 700; }
@media (max-width: 640px) {
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
