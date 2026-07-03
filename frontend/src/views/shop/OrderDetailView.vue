<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageShell from '../../components/PageShell.vue'
import { fetchOrder } from '../../api'

const { t } = useI18n()
const route = useRoute()
const order = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetchOrder(route.params.id)
    order.value = res.data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PageShell>
    <RouterLink to="/my/orders" class="back-link">← {{ t('orders.title') }}</RouterLink>
    <p v-if="loading" class="page-empty">{{ t('common.loading') }}</p>
    <template v-else-if="order">
      <h1 class="page-title">{{ order.order_no }}</h1>
      <dl class="detail-list">
        <div><dt>{{ t('common.status') }}</dt><dd>{{ order.status }}</dd></div>
        <div><dt>{{ t('orders.total') }}</dt><dd>KRW {{ Number(order.total_amount).toLocaleString() }}</dd></div>
        <div><dt>{{ t('orders.date') }}</dt><dd>{{ order.created_at?.slice(0, 16).replace('T', ' ') }}</dd></div>
        <div><dt>{{ t('checkout.name') }}</dt><dd>{{ order.shipping_name }}</dd></div>
        <div><dt>{{ t('checkout.phone') }}</dt><dd>{{ order.shipping_phone }}</dd></div>
        <div><dt>{{ t('checkout.address') }}</dt><dd>{{ order.shipping_address }}</dd></div>
        <div v-if="order.remark"><dt>{{ t('checkout.remark') }}</dt><dd>{{ order.remark }}</dd></div>
      </dl>
      <h2 class="section-sub">{{ t('orders.items') }}</h2>
      <table class="orders-table">
        <thead>
          <tr>
            <th>{{ t('shop.product') }}</th>
            <th>{{ t('shop.quantity') }}</th>
            <th>{{ t('shop.price') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in order.items || []" :key="item.id">
            <td>{{ item.product_name_text || item.product_name }}</td>
            <td>{{ item.quantity }}</td>
            <td>KRW {{ Number(item.line_total || item.unit_price * item.quantity).toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </template>
    <p v-else class="page-empty">{{ t('common.empty') }}</p>
  </PageShell>
</template>

<style scoped lang="scss">
.back-link { display: inline-block; margin-bottom: var(--space-md); font-size: 0.9rem; color: var(--color-steel); }
.detail-list { display: grid; gap: 0.75rem; margin-bottom: var(--space-xl); div { display: grid; grid-template-columns: 8rem 1fr; gap: 0.5rem; font-size: 0.9rem; } dt { opacity: 0.65; } }
.section-sub { font-size: 1.125rem; margin-bottom: var(--space-md); }
.orders-table { width: 100%; border-collapse: collapse; th, td { padding: 0.75rem; border-bottom: 1px solid var(--color-border); text-align: left; } }
</style>
