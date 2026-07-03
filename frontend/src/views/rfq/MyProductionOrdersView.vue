<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchMyProductionOrders } from '../../api'

const { t } = useI18n()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchMyProductionOrders()
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('productionOrder.buyerTitle') }}</h1>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('common.empty') }}</p>
    <table v-else class="order-table">
      <thead>
        <tr>
          <th>{{ t('productionOrder.orderNo') }}</th>
          <th>{{ t('demandHall.rfqNo') }}</th>
          <th>{{ t('myRfqs.supplier') }}</th>
          <th>{{ t('rfq.price') }}</th>
          <th>{{ t('common.status') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in items" :key="o.id">
          <td>
            <RouterLink :to="`/my/production-orders/${o.id}`">{{ o.order_no }}</RouterLink>
          </td>
          <td>{{ o.rfq_no }}</td>
          <td>{{ o.supplier_name }}</td>
          <td>{{ o.currency }} {{ Number(o.price_amount).toLocaleString() }}</td>
          <td>{{ o.status }}</td>
        </tr>
      </tbody>
    </table>
  </PageShell>
</template>

<style scoped lang="scss">
.order-table { width: 100%; border-collapse: collapse; th, td { text-align: left; padding: var(--space-sm); border-bottom: 1px solid var(--color-border); } a { color: var(--color-steel); font-weight: 600; text-decoration: none; } }
</style>
