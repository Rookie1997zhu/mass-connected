<script setup>
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps({
  dashboard: { type: Object, required: true },
})

const { t } = useI18n()
</script>

<template>
  <div class="stat-grid">
    <div class="stat-card"><span class="stat-num">{{ dashboard.points_balance }}</span><span class="stat-label">{{ t('mypage.pointsBalance') }}</span></div>
    <div class="stat-card"><span class="stat-num">{{ dashboard.simple_quotes_count }}</span><span class="stat-label">{{ t('mypage.simpleQuotes') }}</span></div>
    <div class="stat-card"><span class="stat-num">{{ dashboard.rfqs_count }}</span><span class="stat-label">{{ t('mypage.detailQuotes') }}</span></div>
    <div class="stat-card"><span class="stat-num">{{ dashboard.projects_count }}</span><span class="stat-label">{{ t('mypage.projects') }}</span></div>
    <div class="stat-card"><span class="stat-num">{{ dashboard.contracts_count }}</span><span class="stat-label">{{ t('mypage.contracts') }}</span></div>
    <div class="stat-card"><span class="stat-num">{{ dashboard.pending_payments_count }}</span><span class="stat-label">{{ t('mypage.pendingPayments') }}</span></div>
    <div class="stat-card"><span class="stat-num">{{ dashboard.unread_notifications }}</span><span class="stat-label">{{ t('mypage.notifications') }}</span></div>
    <RouterLink to="/simple-quote" class="stat-card stat-card--cta">＋ {{ t('simpleQuote.title') }}</RouterLink>
    <RouterLink to="/my/nda" class="stat-card">{{ t('nda.title') }}</RouterLink>
  </div>
</template>

<style scoped lang="scss">
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--space-md); }
.stat-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); display: flex; flex-direction: column; gap: 0.25rem; text-decoration: none; color: inherit; }
.stat-card--cta { align-items: center; justify-content: center; color: var(--color-steel); font-weight: 600; border-style: dashed; }
.stat-num { font-size: 1.75rem; font-weight: 700; }
.stat-label { font-size: 0.8125rem; opacity: 0.65; }
</style>
