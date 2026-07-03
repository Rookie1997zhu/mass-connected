<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchMyProductionOrder } from '../../api'

const { t } = useI18n()
const route = useRoute()
const order = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchMyProductionOrder(route.params.id)
    order.value = res.data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="order">
      <h1 class="page-title">{{ order.order_no }}</h1>
      <dl class="detail-grid">
        <div><dt>{{ t('demandHall.rfqNo') }}</dt><dd>{{ order.rfq_no }}</dd></div>
        <div><dt>{{ t('myRfqs.supplier') }}</dt><dd>{{ order.supplier_name }}</dd></div>
        <div><dt>{{ t('rfq.price') }}</dt><dd>{{ order.currency }} {{ Number(order.price_amount).toLocaleString() }}</dd></div>
        <div><dt>{{ t('rfq.leadTime') }}</dt><dd>{{ order.lead_time_days }}</dd></div>
        <div><dt>{{ t('common.status') }}</dt><dd>{{ order.status }}</dd></div>
        <div v-if="order.confirmed_at"><dt>{{ t('productionOrder.confirmedAt') }}</dt><dd>{{ order.confirmed_at }}</dd></div>
      </dl>
    </template>
  </PageShell>
</template>

<style scoped lang="scss">
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-md); dt { font-size: 0.8125rem; color: var(--color-text-muted); } dd { margin: 0.25rem 0 0; font-weight: 500; } }
</style>
