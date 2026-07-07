<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchMyFactoryQuotes } from '../../api'
import { useLocaleCurrency } from '../../composables/useLocaleCurrency'

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchMyFactoryQuotes()
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('factory.myQuotesTitle') }}</h1>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('common.empty') }}</p>
    <table v-else class="quote-table">
      <thead>
        <tr>
          <th>{{ t('demandHall.rfqNo') }}</th>
          <th>{{ t('rfq.price') }}</th>
          <th>{{ t('rfq.leadTime') }}</th>
          <th>{{ t('common.status') }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="q in items" :key="q.id">
          <td>{{ q.rfq_no }}</td>
          <td>{{ formatMoney({ amount: q.price_amount, currency: q.currency || 'KRW' }) }}</td>
          <td>{{ q.lead_time_days }}</td>
          <td>{{ q.status }}</td>
          <td>
            <RouterLink :to="`/demand-hall/${q.rfq_id}`" class="btn btn-sm btn-secondary">
              {{ t('demandHall.view') }}
            </RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </PageShell>
</template>

<style scoped lang="scss">
.quote-table { width: 100%; border-collapse: collapse; th, td { padding: 0.75rem; border-bottom: 1px solid var(--color-border); text-align: left; } th { font-size: 0.8125rem; color: var(--color-text-muted); } }
</style>
