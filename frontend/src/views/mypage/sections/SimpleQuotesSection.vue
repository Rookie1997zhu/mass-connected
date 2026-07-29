<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useLocaleCurrency } from '../../../composables/useLocaleCurrency'

defineProps({
  simpleQuotes: { type: Array, default: () => [] },
})

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()

const money = (v, c = 'KRW', quote = null) => {
  if (quote) {
    return formatMoney({
      amount: v,
      currency: quote.currency,
      totalKrw: quote.result?.total_krw,
      rmbToKrw: quote.result?.rmb_to_krw,
    })
  }
  return formatMoney({ amount: v, currency: c })
}
const quoteTypeLabel = (quoteType) => {
  if (quoteType === 'paper_box') return t('packaging.title')
  const key = quoteType === 'print3d' ? 'print3d' : quoteType
  return t(`simpleQuote.${key}`)
}
const quoteDetailLink = (quote) => {
  if (quote.quote_type === 'paper_box') {
    const code = quote.inputs?.box_code
    return code ? `/packaging/box?code=${encodeURIComponent(code)}` : '/packaging'
  }
  return `/simple-quote?id=${quote.id}`
}
</script>

<template>
  <div>
    <RouterLink to="/simple-quote" class="btn btn-primary btn-sm mb">＋ {{ t('simpleQuote.title') }}</RouterLink>
    <RouterLink to="/packaging" class="btn btn-secondary btn-sm mb">＋ {{ t('packaging.title') }}</RouterLink>
    <p v-if="!simpleQuotes.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <table v-else class="data-table">
      <thead><tr><th>No.</th><th>{{ t('simpleQuote.type') }}</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
      <tbody>
        <tr v-for="q in simpleQuotes" :key="q.id">
          <td>{{ q.quote_no }}</td>
          <td>{{ quoteTypeLabel(q.quote_type) }}</td>
          <td>{{ money(q.total_amount, q.currency, q) }}</td>
          <td>{{ q.status }}</td>
          <td><RouterLink :to="quoteDetailLink(q)" class="link">{{ t('demandHall.view') }}</RouterLink></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.mb { margin-bottom: var(--space-md); }
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); cursor: pointer; }
</style>
