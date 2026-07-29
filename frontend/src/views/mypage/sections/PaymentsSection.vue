<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useLocaleCurrency } from '../../../composables/useLocaleCurrency'

defineProps({
  payments: { type: Array, default: () => [] },
})

defineEmits(['upload-proof'])

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
</script>

<template>
  <div>
    <p v-if="!payments.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <table v-else class="data-table">
      <thead><tr><th>No.</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th><th></th></tr></thead>
      <tbody>
        <tr v-for="p in payments" :key="p.id">
          <td>{{ p.payment_no }}</td>
          <td>{{ money(p.amount, p.currency) }}</td>
          <td>{{ p.status }}</td>
          <td class="actions-cell">
            <RouterLink v-if="p.rfq" :to="`/my/rfqs/${p.rfq}`" class="link">{{ t('fulfillment.viewDeal') }}</RouterLink>
            <label v-if="p.status !== 'confirmed'" class="upload-label">
              {{ t('mypage.uploadProof') }}
              <input type="file" hidden @change="(e) => $emit('upload-proof', p, e)" />
            </label>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.link { color: var(--color-steel); cursor: pointer; }
.upload-label { color: var(--color-steel); cursor: pointer; font-size: 0.85rem; }
</style>
