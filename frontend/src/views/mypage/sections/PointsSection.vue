<script setup>
import { useI18n } from 'vue-i18n'
import { useLocaleCurrency } from '../../../composables/useLocaleCurrency'

defineProps({
  wallet: { type: Object, default: null },
  recharges: { type: Array, default: () => [] },
  transactions: { type: Array, default: () => [] },
})

const rechargeAmount = defineModel('rechargeAmount', { type: Number, default: 50000 })

const emit = defineEmits(['recharge-proof-change', 'submit-recharge'])

const { t } = useI18n()
const { formatMoney } = useLocaleCurrency()
</script>

<template>
  <div>
    <div v-if="wallet" class="points-summary">
      <div><span class="stat-num">{{ wallet.balance }}</span><span class="stat-label">{{ t('mypage.balance') }}</span></div>
      <div><span class="stat-num">{{ wallet.total_earned }}</span><span class="stat-label">{{ t('mypage.totalEarned') }}</span></div>
      <div><span class="stat-num">{{ wallet.total_spent }}</span><span class="stat-label">{{ t('mypage.totalSpent') }}</span></div>
    </div>
    <div class="recharge-box">
      <label>{{ t('mypage.rechargeAmount') }}<input v-model.number="rechargeAmount" type="number" min="1000" step="1000" /></label>
      <label class="upload-label">{{ t('mypage.uploadProof') }}<input type="file" @change="emit('recharge-proof-change', $event)" /></label>
      <button type="button" class="btn btn-primary btn-sm" @click="emit('submit-recharge')">{{ t('mypage.submitRecharge') }}</button>
    </div>
    <h3 class="section-sub">{{ t('mypage.rechargeHistory') }}</h3>
    <p v-if="!recharges.length" class="page-empty">{{ t('mypage.empty') }}</p>
    <table v-else class="data-table mb">
      <thead><tr><th>{{ t('mypage.createdAt') }}</th><th>No.</th><th>{{ t('mypage.amount') }}</th><th>{{ t('mypage.status') }}</th></tr></thead>
      <tbody>
        <tr v-for="r in recharges" :key="r.id">
          <td>{{ (r.created_at || '').slice(0, 10) }}</td>
          <td>{{ r.recharge_no }}</td>
          <td>{{ formatMoney({ amount: r.amount_krw, currency: 'KRW' }) }}</td>
          <td>{{ r.status }}</td>
        </tr>
      </tbody>
    </table>
    <h3 class="section-sub">{{ t('mypage.transactionHistory') }}</h3>
    <table class="data-table">
      <thead><tr><th>{{ t('mypage.createdAt') }}</th><th>{{ t('simpleQuote.type') }}</th><th>{{ t('mypage.amount') }}</th></tr></thead>
      <tbody>
        <tr v-for="tx in transactions" :key="tx.id">
          <td>{{ (tx.created_at || '').slice(0, 10) }}</td>
          <td>{{ tx.description || tx.type }}</td>
          <td :class="tx.amount < 0 ? 'neg' : 'pos'">{{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.mb { margin-bottom: var(--space-md); }
.data-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); font-size: 0.9rem; } th { font-size: 0.72rem; text-transform: uppercase; opacity: 0.6; } }
.stat-num { font-size: 1.75rem; font-weight: 700; }
.stat-label { font-size: 0.8125rem; opacity: 0.65; }
.upload-label { color: var(--color-steel); cursor: pointer; font-size: 0.85rem; }
.points-summary { display: flex; gap: var(--space-2xl); margin-bottom: var(--space-lg); div { display: flex; flex-direction: column; } }
.recharge-box { display: flex; gap: var(--space-md); align-items: flex-end; margin-bottom: var(--space-xl); label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.85rem; } input { padding: 0.5rem; border: 1px solid var(--color-border); border-radius: var(--radius-sm); } }
.neg { color: #b91c1c; } .pos { color: #15803d; }
</style>
