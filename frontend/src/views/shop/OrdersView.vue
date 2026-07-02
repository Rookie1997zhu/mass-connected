<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchOrders } from '../../api'

const { t } = useI18n()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchOrders()
    items.value = res.data.items || []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <h1 class="page-title">{{ t('orders.title') }}</h1>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <p v-else-if="!items.length" class="page-empty">{{ t('common.empty') }}</p>
    <table v-else class="orders-table">
      <thead>
        <tr>
          <th>{{ t('orders.orderNo') }}</th>
          <th>{{ t('orders.total') }}</th>
          <th>{{ t('common.status') }}</th>
          <th>{{ t('orders.date') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in items" :key="o.id">
          <td>{{ o.order_no }}</td>
          <td>KRW {{ Number(o.total_amount).toLocaleString() }}</td>
          <td>{{ o.status }}</td>
          <td>{{ o.created_at?.slice(0, 10) }}</td>
        </tr>
      </tbody>
    </table>
  </PageShell>
</template>

<style scoped lang="scss">
.orders-table { width: 100%; border-collapse: collapse; th, td { padding: 0.75rem; border-bottom: 1px solid var(--color-border); text-align: left; } }
</style>
